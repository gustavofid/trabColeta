import json
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


DADOS = Path(__file__).resolve().parents[1] / "dados"
RECORDE = 5.35
FONTE_INCT = "http://vhlab.com.br/INCT/floods/"

CLASSES_RENDA = [
    "Até R$ 2 mil", "R$ 2 a 3 mil", "R$ 3 a 5 mil",
    "R$ 5 a 10 mil", "Mais de R$ 10 mil",
]

# Os trechos identificam as colunas utilizadas na análise exploratória.
INDICADORES_RENDA = {
    "Domicílio com danos": (
        4, "condição estrutural do domicílio depois das enchentes | Com danos",
        "Percentual de domicílios da classe de renda.",
    ),
    "Recebeu auxílio financeiro público": (
        5, "recebeu auxílio financeiro público | Sim",
        "Percentual de domicílios com algum morador que recebeu auxílio.",
    ),
    "Precisou de atendimento médico": (
        5, "Necessidade de atendimento médico de algum morador do domicílio devido às enchentes | Sim",
        "Percentual de domicílios com algum morador que precisou de atendimento.",
    ),
    "Passou ao menos uma noite fora": (
        10, "passar ao menos uma noite fora devido às enchentes | Sim",
        "Percentual de domicílios com algum morador que passou ao menos uma noite fora.",
    ),
    "Perdeu rendimento do trabalho": (
        17, "Existência de perda do rendimento do trabalho | Sim",
        "Percentual de moradores de 14 anos ou mais que trabalhavam, por renda domiciliar.",
    ),
    "Conhece alguma medida preventiva": (
        19, "amenizar os impactos de futuras enchentes | Sim",
        "Percentual de moradores, por renda domiciliar.",
    ),
}


def ler_processado(nome: str) -> pd.DataFrame:
    return pd.read_csv(DADOS / "processados" / nome)


def metadados_peers() -> tuple[str, str]:
    arquivo = DADOS / "originais" / "peers" / "metadados_coleta.json"
    with arquivo.open(encoding="utf-8") as f:
        coleta = json.load(f)["Abrangencia_xlsx.zip"]
    data = datetime.fromisoformat(coleta["data_coleta_utc"]).strftime("%d/%m/%Y")
    return coleta["url"], data


def malha_bairros() -> dict | None:
    """Contornos dos bairros gerados por scripts/mapa_bairros.py, se existirem."""
    arquivo = DADOS / "processados" / "bairros.geojson"
    if not arquivo.exists():
        return None
    return json.loads(arquivo.read_text(encoding="utf-8"))


def curva_populacao(inct: pd.DataFrame) -> pd.Series:
    return inct.groupby("nivel_m")["affected_population"].sum()


def populacao_no_recorde(curva: pd.Series) -> float:
    return float(np.interp(RECORDE, curva.index, curva))


def cenarios_por_nivel(inct: pd.DataFrame, nivel: float) -> pd.DataFrame:
    # Arredonda o valor do controle antes de localizar o décimo no CSV.
    return inct.loc[inct["nivel_m"].eq(round(nivel, 1))]


def percentuais_da_tabela(peers: pd.DataFrame, tabela: int) -> pd.DataFrame:
    return peers.loc[peers["tabela"].eq(tabela) & peers["medida"].eq("percentual")]


def taxas_do_indicador(taxas: pd.DataFrame, tabela: int, trecho: str) -> pd.DataFrame:
    selecionadas = taxas.loc[taxas["tabela"].eq(tabela) & taxas["coluna"].str.contains(trecho, regex=False)]
    return selecionadas.set_index("classe").loc[[*CLASSES_RENDA, "Total"]]


def impactos_do_evento(peers: pd.DataFrame) -> pd.Series:
    t6 = percentuais_da_tabela(peers, 6).set_index("categoria")["valor"]
    t1 = percentuais_da_tabela(peers, 1)
    alguma = t1.loc[
        t1["grupo"].eq("Existência de ocorrências causadas pelas enchentes no domicílio")
        & t1["categoria"].eq("Sim"),
        "valor",
    ].item()
    return pd.Series({
        "Inundação do domicílio": t6.at["Domicílio inundado"],
        "Interrupção de água": t6.at["Interrupção do fornecimento de água"],
        "Ao menos uma ocorrência": alguma,
    })
