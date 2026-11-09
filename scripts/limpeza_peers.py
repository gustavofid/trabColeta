"""Preparação das Tabelas 1 a 21 da PEERS/IBGE (área de abrangência).

Entrada:  dados/originais/peers/Abrangencia_xlsx/Tab1.xlsx ... Tab21.xlsx
Saídas:   dados/processados/peers_longo.csv        (uma linha por tabela, grupo, categoria, coluna e medida)
          dados/processados/peers_taxas_renda.csv  (taxas por classe de renda, para a Tela 2)

Cada planilha tem duas abas com o mesmo desenho: o indicador (TabN_INDICADOR) e o
coeficiente de variação (TabNa_CV). O cabeçalho ocupa várias linhas com células mescladas;
o script "desmescla" o cabeçalho, monta o nome de cada coluna, lê as linhas de dados até a
nota "Fonte:" e junta o CV de cada célula. Detalhes em relatorios/limpeza_dados.pdf.
"""

from __future__ import annotations

import re
from pathlib import Path

import openpyxl
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
PASTA = RAIZ / "dados" / "originais" / "peers" / "Abrangencia_xlsx"
SAIDA = RAIZ / "dados" / "processados" / "peers_longo.csv"
SAIDA_TAXAS = RAIZ / "dados" / "processados" / "peers_taxas_renda.csv"

RENDA_5 = ["Até R$ 2 mil", "R$ 2 a 3 mil", "R$ 3 a 5 mil", "R$ 5 a 10 mil", "Mais de R$ 10 mil"]


def limpa(texto) -> str:
    return re.sub(r"\s+", " ", str(texto)).strip() if texto is not None else ""


def valor_mesclado(ws) -> dict:
    """Mapa (linha, coluna) -> valor, repetindo o valor das células mescladas."""
    mapa = {}
    for faixa in ws.merged_cells.ranges:
        v = ws.cell(faixa.min_row, faixa.min_col).value
        for r in range(faixa.min_row, faixa.max_row + 1):
            for c in range(faixa.min_col, faixa.max_col + 1):
                mapa[(r, c)] = v
    return mapa


def renda_5_classes(rotulo: str) -> str | None:
    """Padroniza as faixas de renda (a Tabela 1 tem 7 classes, as demais 5)."""
    numeros = [float(n.replace(".", "").replace(",", ".")) for n in re.findall(r"[\d.]+,\d{2}", rotulo)]
    if not numeros:
        return None
    if rotulo.lower().startswith("até"):
        return "Até R$ 2 mil" if numeros[0] <= 2000 else None
    if rotulo.lower().startswith("mais de"):
        return "Mais de R$ 10 mil" if numeros[0] >= 10000 else None
    inicio = numeros[0]
    if inicio < 2000:
        return "Até R$ 2 mil"
    if inicio < 3000:
        return "R$ 2 a 3 mil"
    if inicio < 5000:
        return "R$ 3 a 5 mil"
    if inicio < 10000:
        return "R$ 5 a 10 mil"
    return "Mais de R$ 10 mil"


def ler_tabela(numero: int) -> pd.DataFrame:
    wb = openpyxl.load_workbook(PASTA / f"Tab{numero}.xlsx")
    ws, ws_cv = wb.worksheets[0], wb.worksheets[1]
    mesclas = valor_mesclado(ws)
    cel = lambda r, c: mesclas.get((r, c), ws.cell(r, c).value)

    titulo = limpa(ws.cell(1, 1).value)
    universo = limpa(cel(2, 2))

    # primeira linha de dados = primeira linha com número na coluna B
    primeira = next(r for r in range(3, ws.max_row + 1) if isinstance(ws.cell(r, 2).value, (int, float)))

    # nome de cada coluna de valores a partir das linhas de cabeçalho (3 .. primeira-1)
    colunas = {}
    for c in range(2, ws.max_column + 1):
        partes = []
        for r in range(3, primeira):
            t = limpa(cel(r, c))
            if t and (not partes or partes[-1] != t):
                partes.append(t)
        if not partes:
            continue
        medida = "percentual" if "%" in partes[-1] else "total"
        dimensao = [p for p in partes if "%" not in p and not re.fullmatch(r"Total( \(\d\))*", p)]
        colunas[c] = (" | ".join(dimensao) if dimensao else "Total", medida)

    linhas, grupo, subgrupo = [], "Total", None
    for r in range(primeira, ws.max_row + 1):
        rotulo_bruto = str(ws.cell(r, 1).value or "")
        rotulo = limpa(rotulo_bruto)
        recuo = len(rotulo_bruto) - len(rotulo_bruto.lstrip())  # o IBGE indica subgrupos com espaços
        if rotulo.startswith(("Fonte", "Nota", "*")) or re.match(r"^\(\d\)", rotulo):
            break
        valores = {c: ws.cell(r, c).value for c in colunas}
        if not any(isinstance(v, (int, float)) for v in valores.values()):
            if rotulo and recuo:
                subgrupo = rotulo  # subseção recuada (ex.: Tabelas 3 e 16)
            elif rotulo:
                grupo, subgrupo = rotulo, None  # seção (ex.: "Classes de rendimento ...")
            continue
        grupo_linha = f"{grupo} > {subgrupo}" if (recuo and subgrupo) else grupo
        categoria = re.sub(r"\s*\(\d\)(\(\d\))*$", "", rotulo).rstrip(":").strip()
        for c, (coluna, medida) in colunas.items():
            v = valores[c]
            if not isinstance(v, (int, float)):
                continue
            cv = ws_cv.cell(r, c).value
            linhas.append({
                "tabela": numero, "titulo": titulo, "universo": universo,
                "grupo": "Total" if categoria.startswith("Total") else grupo_linha,
                "categoria": categoria, "coluna": coluna, "medida": medida,
                "valor": float(v), "cv_pct": float(cv) if isinstance(cv, (int, float)) else None,
            })
    df = pd.DataFrame(linhas)
    df["grupo"] = df["grupo"].map(lambda g: re.sub(r"\s*\(\d\)$", "", g))
    eh_renda = df["grupo"].str.contains("rendimento", case=False)
    df.loc[eh_renda, "renda_5_classes"] = df.loc[eh_renda, "categoria"].map(renda_5_classes)
    return df


def taxas_por_renda(longo: pd.DataFrame) -> pd.DataFrame:
    """Para cada tabela cruzada por renda: % da classe que está em cada coluna
    (valor da coluna / total da classe). Inclui a linha 'Total' como referência."""
    tot = longo[longo["medida"] == "total"]
    base = tot[tot["coluna"] == "Total"][["tabela", "categoria", "valor"]].rename(columns={"valor": "total_linha"})
    sub = tot[(tot["coluna"] != "Total")
              & (tot["renda_5_classes"].notna() | (tot["grupo"] == "Total"))
              & tot["tabela"].isin(tot.loc[tot["renda_5_classes"].notna(), "tabela"].unique())]
    out = sub.merge(base, on=["tabela", "categoria"])
    out["classe"] = out["renda_5_classes"].fillna("Total")
    out = (out.groupby(["tabela", "titulo", "coluna", "classe"], as_index=False)
              .agg(valor=("valor", "sum"), total_linha=("total_linha", "sum"), cv_pct=("cv_pct", "max")))
    out["taxa_pct"] = (out["valor"] / out["total_linha"] * 100).round(2)
    ordem = {c: i for i, c in enumerate(RENDA_5 + ["Total"])}
    return out.sort_values(["tabela", "coluna", "classe"], key=lambda s: s.map(ordem) if s.name == "classe" else s)


def main() -> None:
    longo = pd.concat([ler_tabela(n) for n in range(1, 22)], ignore_index=True)
    longo["ic95_inf"] = (longo["valor"] * (1 - 1.96 * longo["cv_pct"] / 100)).clip(lower=0)
    longo["ic95_sup"] = longo["valor"] * (1 + 1.96 * longo["cv_pct"] / 100)
    longo["cv_alto"] = longo["cv_pct"] > 15  # faixa C ou pior, segundo as notas do IBGE

    # checagens: total geral de domicílios e moradores
    assert abs(longo.query("tabela == 1 and categoria == 'Total' and coluna == 'Total' and medida == 'total'")
               ["valor"].iloc[0] - 2_328_093) < 1
    assert abs(longo.query("tabela == 2 and categoria == 'Total' and coluna == 'Total' and medida == 'total'")
               ["valor"].iloc[0] - 6_333_727) < 1

    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    longo.to_csv(SAIDA, index=False, encoding="utf-8")
    taxas = taxas_por_renda(longo)
    taxas.to_csv(SAIDA_TAXAS, index=False, encoding="utf-8")
    print(f"[ok] {len(longo)} linhas, {longo['tabela'].nunique()} tabelas em {SAIDA.relative_to(RAIZ)}")
    print(f"[ok] {len(taxas)} taxas por classe de renda em {SAIDA_TAXAS.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
