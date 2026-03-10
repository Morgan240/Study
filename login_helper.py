#!/usr/bin/env python3
"""
login_helper.py — Extrai sessao do Google/NotebookLM do seu browser
--------------------------------------------------------------------
Duas formas de usar:

  FORMA 1 (recomendado): Roda no seu computador LOCAL
  --------------------------------------------------
  pip install 'notebooklm-py[browser]>=0.3.3'
  python login_helper.py --login
  # Isso abre o browser, voce faz login e salva storage_state.json

  FORMA 2: Exporta cookies manualmente do Chrome/Firefox
  -------------------------------------------------------
  1. Abra notebooklm.google.com ja logado
  2. DevTools → Application → Cookies → copie os valores
  3. python login_helper.py --from-cookies
"""

import argparse
import json
import sys
from pathlib import Path


def login_via_playwright():
    """Abre browser para login interativo (roda localmente)."""
    try:
        from notebooklm import NotebookLMClient
    except ImportError:
        print("Instale primeiro: pip install 'notebooklm-py[browser]>=0.3.3'")
        sys.exit(1)

    import subprocess
    result = subprocess.run(
        ["notebooklm", "login"],
        check=False
    )
    if result.returncode == 0:
        storage_path = Path.home() / ".notebooklm" / "storage_state.json"
        if storage_path.exists():
            print(f"\n[OK] Sessao salva em: {storage_path}")
            print("\nAgora copie esse arquivo para o servidor:")
            print(f"  scp {storage_path} usuario@servidor:/root/.notebooklm/storage_state.json")
            print("\nOu imprima o conteudo para colar como variavel de ambiente:")
            print(f"  cat {storage_path}")
        else:
            print("[ERRO] Arquivo de sessao nao encontrado.")
    else:
        print("[ERRO] Login falhou.")


def build_storage_state_from_cookies(cookies: list[dict]) -> dict:
    """Converte cookies do formato DevTools para Playwright storage_state."""
    playwright_cookies = []
    for c in cookies:
        pc = {
            "name": c.get("name", ""),
            "value": c.get("value", ""),
            "domain": c.get("domain", ".google.com"),
            "path": c.get("path", "/"),
            "expires": c.get("expirationDate", c.get("expires", -1)),
            "httpOnly": c.get("httpOnly", False),
            "secure": c.get("secure", True),
            "sameSite": c.get("sameSite", "Lax"),
        }
        playwright_cookies.append(pc)

    return {
        "cookies": playwright_cookies,
        "origins": []
    }


def from_cookies_interactive():
    """Guia o usuario para extrair cookies manualmente."""
    print("""
=== Extraindo sessao do NotebookLM via cookies ===

PASSO 1: Exporte os cookies pelo browser
-----------------------------------------
Chrome / Edge:
  1. Abra https://notebooklm.google.com (ja logado)
  2. F12 → Console
  3. Cole e execute este comando:
     copy(document.cookie)

  Ou use a extensao "EditThisCookie" para exportar como JSON.

Firefox:
  1. Abra https://notebooklm.google.com (ja logado)
  2. F12 → Storage → Cookies → https://notebooklm.google.com
  3. Selecione todos os cookies e copie

PASSO 2: Cole a string de cookies abaixo
-----------------------------------------
Formato esperado: name1=value1; name2=value2; ...
(ou JSON exportado pela extensao)
""")

    cookie_input = input("Cole os cookies aqui: ").strip()
    if not cookie_input:
        print("[ERRO] Nenhum cookie fornecido.")
        return

    cookies = []

    # Tenta parsear como JSON primeiro
    if cookie_input.startswith("["):
        try:
            raw = json.loads(cookie_input)
            for c in raw:
                cookies.append({
                    "name": c.get("name", ""),
                    "value": c.get("value", ""),
                    "domain": c.get("domain", ".google.com"),
                    "path": c.get("path", "/"),
                    "expires": c.get("expirationDate", -1),
                    "httpOnly": c.get("httpOnly", False),
                    "secure": c.get("secure", True),
                    "sameSite": "Lax",
                })
        except json.JSONDecodeError:
            pass

    # Tenta parsear como "key=value; key=value"
    if not cookies and "=" in cookie_input:
        for pair in cookie_input.split(";"):
            pair = pair.strip()
            if "=" in pair:
                name, _, value = pair.partition("=")
                cookies.append({
                    "name": name.strip(),
                    "value": value.strip(),
                    "domain": ".google.com",
                    "path": "/",
                    "expires": -1,
                    "httpOnly": False,
                    "secure": True,
                    "sameSite": "Lax",
                })

    if not cookies:
        print("[ERRO] Nao foi possivel parsear os cookies.")
        return

    storage = build_storage_state_from_cookies(cookies)

    out_path = Path("/root/.notebooklm/storage_state.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(storage, indent=2))

    print(f"\n[OK] storage_state.json salvo em: {out_path}")
    print(f"     {len(cookies)} cookies salvos.")
    print("\nTestando autenticacao...")

    import subprocess
    result = subprocess.run(["notebooklm", "auth", "check"], capture_output=True, text=True)
    print(result.stdout or result.stderr)


def main():
    parser = argparse.ArgumentParser(description="Helper de login para NotebookLM")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--login", action="store_true",
                       help="Login interativo via browser (rode localmente)")
    group.add_argument("--from-cookies", action="store_true",
                       help="Cria sessao a partir de cookies copiados do browser")
    group.add_argument("--print-instructions", action="store_true",
                       help="Imprime instrucoes detalhadas")
    args = parser.parse_args()

    if args.login:
        login_via_playwright()
    elif args.from_cookies:
        from_cookies_interactive()
    elif args.print_instructions:
        print(__doc__)


if __name__ == "__main__":
    main()
