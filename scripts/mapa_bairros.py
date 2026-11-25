"""Prepara a malha oficial de bairros de Porto Alegre para o mapa da Tela 1.

Entrada:  dados/originais/bairros/bairros_2016.geojson  (limites oficiais da Lei
          12.112/2016, publicados no servidor de mapas da Prefeitura)
Saída:    dados/processados/bairros.geojson

O script converte a malha para WGS 84 (latitude/longitude), simplifica o contorno
para o mapa carregar rápido e casa os nomes com os do INCT sem diferenciar
acentos, apóstrofos, hífens e maiúsculas.

Uso:
    python scripts/mapa_bairros.py
"""

from __future__ import annotations

import json
import re
import unicodedata
from datetime import date
from pathlib import Path

import geopandas as gpd
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
ENTRADA = RAIZ / "dados" / "originais" / "bairros"
INCT = RAIZ / "dados" / "processados" / "inct_longo_limpo.csv"
SAIDA = RAIZ / "dados" / "processados" / "bairros.geojson"
ARQUIVO = ENTRADA / "bairros_2016.geojson"
FONTE = ("https://gis-smamus.portoalegre.rs.gov.br/server/rest/services/"
         "01_PUBLICACOES/bairros_2016/MapServer")

TOLERANCIA_M = 10  # simplificação do contorno, em metros

# Grafias que diferem além de acentos e pontuação: {nome na malha: nome no INCT}
APELIDOS: dict[str, str] = {
    "CEL. APARICIO BORGES": "Coronel Aparício Borges",
    "PASSO DA AREIA": "Passo D'Areia",
}


def chave(nome: str) -> str:
    """'Mont'Serrat' -> 'montserrat'."""
    sem_acento = unicodedata.normalize("NFKD", str(nome)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", sem_acento.lower())


def main() -> None:
    if not ARQUIVO.exists():
        raise SystemExit(f"Falta {ARQUIVO.relative_to(RAIZ)}. Fonte: {FONTE}")
    malha = gpd.read_file(ARQUIVO)

    nomes_inct = pd.read_csv(INCT)["bairro"].unique()
    por_chave = {chave(n): n for n in nomes_inct}
    por_chave.update({chave(malha_): por_chave[chave(inct)] for malha_, inct in APELIDOS.items()})

    # a coluna de nomes é a que mais casa com os bairros do INCT
    textos = [c for c in malha.columns if c != malha.geometry.name]
    coluna = max(textos, key=lambda c: malha[c].map(chave).isin(por_chave).sum())
    malha["bairro"] = malha[coluna].map(chave).map(por_chave)

    sobraram = sorted(malha.loc[malha["bairro"].isna(), coluna].astype(str))
    faltaram = sorted(set(nomes_inct) - set(malha["bairro"].dropna()))

    malha = malha.dropna(subset=["bairro"])[["bairro", "geometry"]].dissolve("bairro", as_index=False)
    malha = malha.to_crs(31982)  # SIRGAS 2000 / UTM 22S, em metros
    malha["geometry"] = malha.geometry.simplify(TOLERANCIA_M, preserve_topology=True)
    malha = malha.to_crs(4326)

    geojson = json.loads(malha.to_json())
    geojson["metadados"] = {
        "fonte": FONTE,
        "data_coleta": date.fromtimestamp(ARQUIVO.stat().st_mtime).isoformat(),
    }
    SAIDA.write_text(json.dumps(geojson, ensure_ascii=False), encoding="utf-8")

    print(f"[ok] {len(malha)} de {len(nomes_inct)} bairros em {SAIDA.relative_to(RAIZ)} "
          f"(coluna de nomes: {coluna})")
    if faltaram:
        print(f"[aviso] bairros do INCT sem contorno: {faltaram}")
    if sobraram:
        print(f"[aviso] nomes da malha sem par no INCT: {sobraram}")


if __name__ == "__main__":
    main()
