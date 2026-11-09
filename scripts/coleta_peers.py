"""Coleta automatizada da PEERS (IBGE).

Pesquisa Especial sobre as Enchentes de 2024 no Rio Grande do Sul.
Fonte: https://ftp.ibge.gov.br/Meio_Ambiente/PEERS/2024/

O script:
  1. baixa o .zip com as Tabelas 1 a 21 em xlsx (área de abrangência da
     pesquisa), o mesmo conjunto usado no projeto;
  2. NÃO baixa de novo o que já existe em dados/originais/peers/
     (coleta responsável: os dados brutos ficam guardados localmente);
  3. extrai os .zip;
  4. registra URL, data/hora da coleta, tamanho e SHA-256 de cada arquivo em
     dados/originais/peers/metadados_coleta.json.

Uso:
    python scripts/coleta_peers.py            # baixa só o que falta
    python scripts/coleta_peers.py --forcar   # baixa tudo de novo
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import requests

URL_BASE = "https://ftp.ibge.gov.br/Meio_Ambiente/PEERS/2024/"
ARQUIVOS = [
    "Abrangencia_xlsx.zip",  # Tabelas 1 a 21 (área de abrangência da pesquisa)
]

RAIZ = Path(__file__).resolve().parents[1]
DESTINO = RAIZ / "dados" / "originais" / "peers"
METADADOS = DESTINO / "metadados_coleta.json"

HEADERS = {"User-Agent": "projeto-enchentes-pucrs/1.0 (trabalho academico)"}
PAUSA_SEGUNDOS = 2  # intervalo entre requisições, para não sobrecarregar o servidor


def sha256(caminho: Path) -> str:
    h = hashlib.sha256()
    with caminho.open("rb") as f:
        for bloco in iter(lambda: f.read(1 << 16), b""):
            h.update(bloco)
    return h.hexdigest()


def baixar(nome: str, forcar: bool) -> dict:
    url = URL_BASE + nome
    caminho = DESTINO / nome
    if caminho.exists() and not forcar:
        print(f"[ok] {nome} já existe, pulando download")
        return {"arquivo": nome, "url": url, "baixado_agora": False}

    print(f"[..] baixando {url}")
    resp = requests.get(url, headers=HEADERS, timeout=120)
    resp.raise_for_status()
    caminho.write_bytes(resp.content)
    time.sleep(PAUSA_SEGUNDOS)
    return {
        "arquivo": nome,
        "url": url,
        "baixado_agora": True,
        "data_coleta_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "last_modified_servidor": resp.headers.get("Last-Modified"),
        "bytes": caminho.stat().st_size,
        "sha256": sha256(caminho),
    }


def extrair(caminho_zip: Path) -> None:
    pasta = caminho_zip.with_suffix("")  # Abrangencia_xlsx.zip -> Abrangencia_xlsx/
    pasta.mkdir(exist_ok=True)
    with zipfile.ZipFile(caminho_zip) as z:
        # extrai "achatado": ignora pastas internas do zip, para que as tabelas
        # fiquem sempre em dados/originais/peers/<nome_do_zip>/TabN.xlsx
        for membro in z.infolist():
            nome = Path(membro.filename).name
            if membro.is_dir() or nome.startswith(("~$", ".")):
                continue
            (pasta / nome).write_bytes(z.read(membro))
    print(f"[ok] extraído em {pasta.relative_to(RAIZ)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--forcar", action="store_true", help="baixa de novo mesmo se já existir")
    args = parser.parse_args()

    DESTINO.mkdir(parents=True, exist_ok=True)
    historico = json.loads(METADADOS.read_text(encoding="utf-8")) if METADADOS.exists() else {}

    for nome in ARQUIVOS:
        info = baixar(nome, args.forcar)
        if info["baixado_agora"]:
            historico[nome] = info
        if nome.endswith(".zip"):
            extrair(DESTINO / nome)

    METADADOS.write_text(json.dumps(historico, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[ok] metadados em {METADADOS.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
