# Agente Expert — Template

> Este arquivo e gerado automaticamente pelo `workflow.py`.
> Voce tambem pode preenche-lo manualmente como system prompt para Claude.

---

## Como Usar

### Opcao 1 — Com Claude Code (recomendado)

```bash
# Cole o conteudo deste arquivo como system prompt em qualquer conversa:
cat agents/nome_do_expert.md | pbcopy   # Mac
cat agents/nome_do_expert.md | xclip    # Linux

# Ou use diretamente no Claude Code:
claude --print "$(cat agents/nome_do_expert.md)"
```

### Opcao 2 — Explorar via NotebookLM

```bash
# Autentica (uma vez):
notebooklm login

# Ativa o notebook do expert:
notebooklm use <NOTEBOOK_ID>

# Faz perguntas:
notebooklm ask "Como aplicar o framework X no meu negocio?"
notebooklm ask "Quais sao os 3 primeiros passos para comecar?"

# Gera artefatos:
notebooklm generate audio "resumo dos principais ensinamentos"
notebooklm generate report "guia pratico para aplicar no meu negocio"
notebooklm generate quiz "teste de conhecimento sobre os conceitos principais"
```

### Opcao 3 — Workflow completo (para novo expert)

```bash
# 1. Copie e edite o config:
cp expert_config.yaml experts/meu_expert.yaml
# Edite experts/meu_expert.yaml com nome, fontes e contexto

# 2. Rode o workflow:
python workflow.py --config experts/meu_expert.yaml

# 3. O agente sera salvo em:
#    agents/nome_do_expert.md
```

---

## Estrutura do Agente Gerado

O `workflow.py` gera um arquivo `agents/<nome>.md` com:

```
# Agente: Nome do Expert

## Identidade
Como se comportar, estilo de comunicacao

## Contexto de Negocio do Usuario
Seu negocio e desafios (voce preenche no config)

## Perfil Completo (Q&A NotebookLM)
10+ perguntas e respostas geradas pelo NotebookLM

## Briefing Document
Resumo completo e detalhado do conteudo

## Study Guide
Guia de estudos organizado por topicos

## System Prompt Sugerido
Prompt pronto para usar em outras IAs

## Fontes Originais
Lista de todos os URLs indexados
```

---

## Comandos Rapidos

```bash
# Listar todos seus notebooks:
notebooklm list

# Ver status atual:
notebooklm status

# Adicionar nova fonte a notebook ativo:
notebooklm source add https://youtube.com/watch?v=...

# Listar fontes do notebook ativo:
notebooklm source list

# Gerar audio (podcast) sobre um topico:
notebooklm generate audio "explique o conceito X de forma simples"

# Gerar mind map:
notebooklm generate mind-map

# Exportar artefato para Google Docs:
notebooklm artifact export <artifact-id>

# Historico da conversa:
notebooklm history
```

---

*Para criar seu primeiro agente expert, edite `expert_config.yaml` e rode `python workflow.py`.*
