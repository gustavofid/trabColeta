"""Limpeza da simulação de inundação do INCT SiMAI (data.json).

Entrada:  dados/originais/inct/data.json
Saídas:   dados/processados/inct_longo_limpo.csv   (uma linha por nível e bairro)
          dados/processados/inct_correcoes.csv     (log de cada valor alterado)

Regras aplicadas, na ordem (detalhes e justificativas em relatorios/limpeza_dados.pdf):
  1. Nomes de bairros com acentuação corrompida (UTF-8 lido como Latin-1) são corrigidos.
  2. O nível vem da chave ("5_3m" -> 5.3); bairros são unidos pelo nome, não pela posição.
  3. Prédios afetados nunca podem diminuir quando o rio sobe. Por bairro:
     a. zero no meio de valores positivos                         -> interpolação linear
     b. pico isolado (mais que o dobro dos dois vizinhos)          -> interpolação linear
     c. valor maior que algum valor de nível mais alto em mais de
        5% dos prédios do bairro (impossível pela regra)          -> próximo valor válido
     d. oscilações pequenas restantes                              -> máximo acumulado
  4. percentage e affected_population são recalculados a partir dos prédios corrigidos.
     A população afetada passa a ser calculada sem arredondar o percentual antes
     (o original arredondava duas vezes para cima). Os valores originais ficam em colunas *_original.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
ENTRADA = RAIZ / "dados" / "originais" / "inct" / "data.json"
SAIDA = RAIZ / "dados" / "processados" / "inct_longo_limpo.csv"
LOG = RAIZ / "dados" / "processados" / "inct_correcoes.csv"

LIMIAR_INCOMPATIVEL = 0.05  # regra 3c: 5% do total de prédios do bairro


def corrigir_nome(nome: str) -> str:
    """Desfaz 'ArquipÃ©lago' -> 'Arquipélago' (texto UTF-8 decodificado como Latin-1)."""
    try:
        return nome.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return nome


def carregar() -> pd.DataFrame:
    with ENTRADA.open(encoding="utf-8") as f:
        raw = json.load(f)
    df = pd.DataFrame([
        {"nivel_m": round(float(nivel.removesuffix("m").replace("_", ".")), 1),
         "bairro_original": bairro, **valores}
        for nivel, bairros in raw.items()
        for bairro, valores in bairros.items()
    ])
    df["bairro"] = df["bairro_original"].map(corrigir_nome)
    return df


def corrigir_serie(serie: pd.Series, total: int) -> tuple[pd.Series, dict]:
    """Recebe affected_buildings de um bairro (índice = nível) e devolve a série corrigida
    e um dicionário {nível: regra aplicada}."""
    s = serie.astype(float).copy()
    regras: dict[float, str] = {}
    v = s.values
    n = len(v)

    for i in range(1, n - 1):
        anterior, atual, seguinte = v[i - 1], v[i], v[i + 1]
        # 3a: zero no meio de valores positivos (o bairro já estava alagado e volta a estar)
        if atual == 0 and (v[:i] > 0).any() and (v[i + 1:] > 0).any():
            regras[s.index[i]] = "3a zero no meio da série -> interpolado"
        # 3b: pico isolado
        elif atual > 2 * max(anterior, seguinte) and atual - max(anterior, seguinte) > 100:
            regras[s.index[i]] = "3b pico isolado -> interpolado"
    for nivel in regras:
        s.loc[nivel] = np.nan
    s = s.interpolate(method="index", limit_area="inside")

    # 3c: valores incompatíveis com níveis mais altos
    minimo_futuro = s[::-1].cummin()[::-1].shift(-1)
    incompat = (s - minimo_futuro) > LIMIAR_INCOMPATIVEL * total
    for nivel in s.index[incompat.fillna(False)]:
        regras[nivel] = "3c maior que níveis mais altos -> próximo valor válido"
        s.loc[nivel] = np.nan
    s = s.bfill()

    # 3d: oscilações pequenas
    acumulado = s.cummax()
    for nivel in s.index[acumulado > s]:
        regras.setdefault(nivel, "3d oscilação pequena -> máximo acumulado")
    s = acumulado.round()
    return s, regras


def main() -> None:
    df = carregar()
    df = df.sort_values(["bairro", "nivel_m"]).reset_index(drop=True)
    for col in ["affected_buildings", "percentage", "affected_population"]:
        df[f"{col}_original"] = df[col]

    log = []
    df["correcao"] = ""
    for bairro, grupo in df.groupby("bairro"):
        total = int(grupo["total_buildings"].iloc[0])
        serie = grupo.set_index("nivel_m")["affected_buildings"]
        corrigida, regras = corrigir_serie(serie, total)
        idx = grupo.index
        df.loc[idx, "affected_buildings"] = corrigida.values.astype(int)
        for nivel, regra in regras.items():
            linha = idx[grupo["nivel_m"].values == nivel][0]
            df.loc[linha, "correcao"] = regra
            log.append({"bairro": bairro, "nivel_m": nivel, "regra": regra,
                        "antes": int(serie.loc[nivel]), "depois": int(corrigida.loc[nivel])})

    # 4. recálculo
    df["percentage"] = (df["affected_buildings"] / df["total_buildings"] * 100).round(2)
    df["affected_population"] = (df["population"] * df["affected_buildings"]
                                 / df["total_buildings"]).round().astype(int)

    # checagens finais
    assert df.groupby("nivel_m")["bairro"].nunique().eq(94).all()
    assert (df["affected_buildings"] <= df["total_buildings"]).all()
    assert df.groupby("bairro")["affected_buildings"].apply(lambda s: s.is_monotonic_increasing).all()

    colunas = ["nivel_m", "bairro", "total_buildings", "affected_buildings", "percentage",
               "population", "affected_population", "affected_buildings_original",
               "percentage_original", "affected_population_original", "correcao"]
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    df[colunas].sort_values(["nivel_m", "bairro"]).to_csv(SAIDA, index=False, encoding="utf-8")
    pd.DataFrame(log).sort_values(["bairro", "nivel_m"]).to_csv(LOG, index=False, encoding="utf-8")

    nomes = (df["bairro"] != df["bairro_original"]).groupby(df["bairro"]).any().sum()
    print(f"[ok] {len(df)} linhas em {SAIDA.relative_to(RAIZ)}")
    print(f"[ok] {nomes} nomes de bairro corrigidos; {len(log)} valores corrigidos "
          f"(log em {LOG.relative_to(RAIZ)})")


if __name__ == "__main__":
    main()
