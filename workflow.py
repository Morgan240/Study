#!/usr/bin/env python3
"""
NotebookLM Expert Workflow
--------------------------
Automates the creation of an "expert agent" from public content (YouTube, Substack, Medium).

Usage:
    # 1. Authenticate once:
    notebooklm login

    # 2. Create / edit your expert_config.yaml

    # 3. Run the workflow:
    python workflow.py --config expert_config.yaml

    # 4. Optional: resume with existing notebook ID
    python workflow.py --config expert_config.yaml --notebook-id <id>
"""

import asyncio
import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

import yaml

try:
    from notebooklm import NotebookLMClient
    from notebooklm.exceptions import NotebookLMError
except ImportError:
    print("ERROR: notebooklm-py not installed.")
    print("Run: pip install 'notebooklm-py[browser]>=0.3.3'")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9_-]", "_", text.lower())


def print_step(msg: str):
    print(f"\n{'='*60}\n  {msg}\n{'='*60}")


def print_ok(msg: str):
    print(f"  [OK] {msg}")


def print_warn(msg: str):
    print(f"  [!!] {msg}")


# ---------------------------------------------------------------------------
# Core workflow
# ---------------------------------------------------------------------------

async def run(config: dict, notebook_id: str | None, output_dir: Path):
    expert_name = config["expert"]["name"]
    sources: list[str] = config.get("sources", [])
    extra_questions: list[str] = config.get("extra_questions", [])

    output_dir.mkdir(parents=True, exist_ok=True)

    async with NotebookLMClient.from_storage() as client:

        # ------------------------------------------------------------------
        # 1. Notebook — create or reuse
        # ------------------------------------------------------------------
        print_step(f"1/5  Notebook para: {expert_name}")

        if notebook_id:
            print_ok(f"Usando notebook existente: {notebook_id}")
            nb_id = notebook_id
        else:
            notebook_title = f"Expert: {expert_name}"
            nb = await client.notebooks.create(notebook_title)
            nb_id = nb.notebook_id
            print_ok(f"Criado: '{notebook_title}' → {nb_id}")

        # ------------------------------------------------------------------
        # 2. Add sources
        # ------------------------------------------------------------------
        print_step(f"2/5  Adicionando {len(sources)} fontes")

        added = 0
        for url in sources:
            try:
                await client.sources.add_url(nb_id, url)
                print_ok(url)
                added += 1
            except NotebookLMError as e:
                print_warn(f"Falhou ({url}): {e}")

        if added == 0 and not notebook_id:
            print_warn("Nenhuma fonte adicionada. Verifique os URLs no config.")

        # ------------------------------------------------------------------
        # 3. Wait for indexing
        # ------------------------------------------------------------------
        print_step("3/5  Aguardando indexacao das fontes…")
        await asyncio.sleep(10)  # initial grace period

        sources_list = await client.sources.list(nb_id)
        pending = [s for s in sources_list if getattr(s, "state", None) != "PROCESSED"]
        if pending:
            print_warn(f"{len(pending)} fonte(s) ainda processando — aguardando 30s…")
            await asyncio.sleep(30)
        else:
            print_ok("Todas as fontes indexadas.")

        # ------------------------------------------------------------------
        # 4. Generate artifacts
        # ------------------------------------------------------------------
        print_step("4/5  Gerando artefatos via NotebookLM")

        # Briefing document (comprehensive summary)
        print("  → Gerando Briefing Document…")
        briefing_text = ""
        try:
            briefing_artifact = await client.artifacts.generate_report(
                nb_id,
                instructions=(
                    f"Crie um briefing document completo e detalhado sobre {expert_name}. "
                    "Inclua: principais frameworks, metodologias, conceitos-chave, "
                    "filosofia de trabalho, frases marcantes, e aplicacoes praticas."
                ),
            )
            # Wait for generation
            briefing_artifact = await client.artifacts.wait(nb_id, briefing_artifact.artifact_id)
            briefing_text = briefing_artifact.content or ""
            print_ok("Briefing Document gerado.")
        except Exception as e:
            print_warn(f"Briefing falhou: {e}")

        # Study guide
        print("  → Gerando Study Guide…")
        study_text = ""
        try:
            study_artifact = await client.artifacts.generate_report(
                nb_id,
                instructions=(
                    f"Crie um study guide sobre os principais ensinamentos de {expert_name}. "
                    "Organize por topicos com bullets, exemplos e citacoes diretas."
                ),
            )
            study_artifact = await client.artifacts.wait(nb_id, study_artifact.artifact_id)
            study_text = study_artifact.content or ""
            print_ok("Study Guide gerado.")
        except Exception as e:
            print_warn(f"Study guide falhou: {e}")

        # ------------------------------------------------------------------
        # 5. Q&A to build expert profile
        # ------------------------------------------------------------------
        print_step("5/5  Construindo perfil do expert via perguntas")

        base_questions = [
            f"Quem é {expert_name} e qual é sua área de especialidade principal?",
            f"Quais são os 5 principais frameworks ou metodologias que {expert_name} usa ou ensina?",
            f"Qual é a filosofia central ou visão de mundo de {expert_name}?",
            f"Como {expert_name} se comunica? Descreva o tom, estilo e linguagem que ele/ela usa.",
            f"Quais são as frases, expressoes ou jargoes favoritos de {expert_name}?",
            f"Quais são os maiores erros que {expert_name} diz que as pessoas cometem na sua area?",
            f"Como {expert_name} responderia a um iniciante que quer comecar na sua area?",
            f"Quais livros, ferramentas ou recursos {expert_name} mais recomenda?",
            f"Quais são os casos de sucesso ou exemplos concretos que {expert_name} mais usa?",
            f"Se {expert_name} fosse um agente de IA, qual seria seu system prompt?",
        ] + extra_questions

        qa_results = {}
        for question in base_questions:
            try:
                answer = await client.chat.ask(nb_id, question)
                qa_results[question] = answer.response if hasattr(answer, "response") else str(answer)
                print_ok(f"Q: {question[:60]}…")
            except Exception as e:
                print_warn(f"Pergunta falhou: {e}")
                qa_results[question] = f"[Erro: {e}]"

        # ------------------------------------------------------------------
        # Build expert.md
        # ------------------------------------------------------------------
        _write_expert_md(
            output_dir=output_dir,
            expert_name=expert_name,
            config=config,
            notebook_id=nb_id,
            briefing=briefing_text,
            study_guide=study_text,
            qa=qa_results,
        )

        print_step("CONCLUIDO")
        print_ok(f"Notebook ID: {nb_id}")
        print_ok(f"Arquivos salvos em: {output_dir}/")
        print(
            f"\n  Para continuar explorando:\n"
            f"    notebooklm use {nb_id}\n"
            f"    notebooklm ask 'Sua pergunta aqui'\n"
        )


# ---------------------------------------------------------------------------
# expert.md builder
# ---------------------------------------------------------------------------

def _write_expert_md(
    output_dir: Path,
    expert_name: str,
    config: dict,
    notebook_id: str,
    briefing: str,
    study_guide: str,
    qa: dict,
):
    sources = config.get("sources", [])
    description = config.get("expert", {}).get("description", "")
    context = config.get("expert", {}).get("business_context", "")

    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    system_prompt_answer = qa.get(
        [q for q in qa if "system prompt" in q.lower()][0]
        if any("system prompt" in q.lower() for q in qa) else "",
        "",
    )

    lines = [
        f"# Agente: {expert_name}",
        f"\n> Gerado automaticamente em {now} via NotebookLM  ",
        f"> Notebook ID: `{notebook_id}`",
        "",
        "---",
        "",
        "## Identidade",
        "",
        f"Voce e um agente que se comporta como **{expert_name}**.",
        f"{description}",
        "",
        "Ao responder, voce:",
        f"- Usa o estilo, tom e vocabulario de {expert_name}",
        "- Cita exemplos, casos e frameworks que ele/ela usa nos seus conteudos",
        "- E direto, pratico e orientado a resultados",
        "- Quando nao sabe algo, diz honestamente e sugere onde pesquisar",
        "",
        "---",
        "",
        "## Contexto de Negocio do Usuario",
        "",
        context or "_Preencha aqui seu contexto de negocio para personalizar as respostas._",
        "",
        "---",
        "",
        "## Como Usar Este Agente",
        "",
        "```",
        "# No Claude Code, cole o conteudo deste arquivo como system prompt:",
        "# ou use: claude --system-prompt expert.md",
        "",
        "# Para explorar via NotebookLM diretamente:",
        f"notebooklm use {notebook_id}",
        "notebooklm ask 'Sua pergunta aqui'",
        "```",
        "",
        "---",
        "",
    ]

    # Q&A section
    lines += ["## Perfil Completo (Q&A NotebookLM)", ""]
    for question, answer in qa.items():
        lines += [f"### {question}", "", answer or "_Sem resposta._", ""]

    # Briefing
    if briefing:
        lines += ["---", "", "## Briefing Document", "", briefing, ""]

    # Study guide
    if study_guide:
        lines += ["---", "", "## Study Guide", "", study_guide, ""]

    # System prompt suggestion
    if system_prompt_answer:
        lines += [
            "---",
            "",
            "## System Prompt Sugerido (para usar em IAs)",
            "",
            "```",
            system_prompt_answer,
            "```",
            "",
        ]

    # Sources
    lines += [
        "---",
        "",
        "## Fontes Originais",
        "",
    ]
    for src in sources:
        lines.append(f"- {src}")

    expert_file = output_dir / f"{slug(expert_name)}.md"
    expert_file.write_text("\n".join(lines), encoding="utf-8")
    print_ok(f"expert.md salvo: {expert_file}")

    # Also save raw Q&A as JSON for future use
    raw_file = output_dir / f"{slug(expert_name)}_raw.json"
    raw_file.write_text(
        json.dumps(
            {"notebook_id": notebook_id, "expert": expert_name, "qa": qa},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print_ok(f"Raw JSON salvo: {raw_file}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="NotebookLM Expert Workflow — cria agente .md a partir de conteudos publicos",
    )
    parser.add_argument(
        "--config",
        default="expert_config.yaml",
        help="Caminho para o arquivo de configuracao YAML (default: expert_config.yaml)",
    )
    parser.add_argument(
        "--notebook-id",
        default=None,
        help="Reusar notebook existente (pula criacao e adicao de fontes)",
    )
    parser.add_argument(
        "--output-dir",
        default="./agents",
        help="Diretorio de saida para os arquivos gerados (default: ./agents)",
    )
    args = parser.parse_args()

    config = load_config(args.config)
    output_dir = Path(args.output_dir)

    asyncio.run(run(config, args.notebook_id, output_dir))


if __name__ == "__main__":
    main()
