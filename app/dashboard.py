from textwrap import wrap

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dados import (
    CLASSES_RENDA,
    FONTE_INCT,
    INDICADORES_RENDA,
    RECORDE,
    cenarios_por_nivel,
    curva_populacao,
    impactos_do_evento,
    ler_processado,
    malha_bairros,
    metadados_peers,
    percentuais_da_tabela,
    populacao_no_recorde,
    taxas_do_indicador,
)


AZUL = "#285779"
VERDE = "#187971"
AZUL_CLARO = "#7297AB"
LARANJA = "#A14D25"
CINZA = "#627686"

ler_csv = st.cache_data(show_spinner=False)(ler_processado)
ler_malha = st.cache_data(show_spinner=False)(malha_bairros)


def numero(valor: float, decimais: int = 0) -> str:
    return f"{valor:,.{decimais}f}".translate(str.maketrans(",.", ".,"))


def mostrar_grafico(figura: go.Figure, altura: int) -> None:
    figura.update_layout(
        height=altura,
        margin=dict(l=6, r=14, t=14, b=10),
        separators=",.",
        showlegend=False,
    )
    st.plotly_chart(figura, use_container_width=True, config={"displayModeBar": False})


def barras_percentuais(
    categorias: pd.Series, valores: pd.Series, cor, erro=None, erro_negativo=None,
    detalhes=None, texto_hover: str = "",
) -> go.Figure:
    rotulos = ["<br>".join(wrap(categoria, 43)) for categoria in categorias]
    figura = go.Figure(go.Bar(
        x=valores,
        y=rotulos,
        orientation="h",
        marker_color=cor,
        error_x=dict(array=erro, arrayminus=erro_negativo, color=CINZA, thickness=1.3)
        if erro is not None else None,
        customdata=detalhes,
        hovertemplate=f"%{{y}}<br>%{{x:.1f}}%{texto_hover}<extra></extra>",
    ))
    figura.update_xaxes(range=[0, 100], ticksuffix="%", title="Percentual")
    figura.update_yaxes(automargin=True, autorange="reversed")
    return figura


def mostrar_mapa(cenario: pd.DataFrame, malha: dict) -> None:
    st.subheader("Mapa dos bairros por percentual de prédios afetados")
    detalhes = ["percentage", "affected_buildings", "total_buildings"]
    modelo = ("<b>%{location}</b><br>%{customdata[0]:.1f}% dos prédios"
              "<br>%{customdata[1]:,.0f} de %{customdata[2]:,.0f} prédios<extra></extra>")
    atingido = cenario["affected_buildings"].gt(0)
    figura = go.Figure()
    # Bairros não atingidos ficam em cinza, fora da escala de cor.
    for linhas, escala, mostrar_escala in (
        (cenario.loc[~atingido], [[0, "#D5DADD"], [1, "#D5DADD"]], False),
        (cenario.loc[atingido], [[0, "#C6DBEA"], [0.5, "#6A9BBF"], [1, "#123A5A"]], True),
    ):
        figura.add_trace(go.Choroplethmap(
            geojson=malha, featureidkey="properties.bairro", locations=linhas["bairro"],
            z=linhas["percentage"], zmin=0, zmax=100, colorscale=escala,
            showscale=mostrar_escala, colorbar=dict(title="% de prédios", ticksuffix="%"),
            marker=dict(opacity=0.8, line=dict(color="#FFFFFF", width=0.8)),
            customdata=linhas[detalhes].to_numpy(), hovertemplate=modelo,
        ))
    figura.update_layout(map=dict(style="carto-positron", center=dict(lat=-30.1, lon=-51.16), zoom=9.6))
    mostrar_grafico(figura, 560)
    metadados = malha["metadados"]
    data = "/".join(reversed(metadados["data_coleta"].split("-")))
    st.caption(
        "Em cinza, bairros sem prédios afetados no nível escolhido. A cor indica o percentual "
        "de prédios do bairro inteiro, não a área alagada. Limites: "
        f"[Bairros oficiais (Lei 12.112/2016), Prefeitura de Porto Alegre]({metadados['fonte']}), coletados em {data}."
    )


def simular(inct: pd.DataFrame, curva: pd.Series) -> None:
    st.header("Simulação do Guaíba")
    st.write("Quais bairros de Porto Alegre seriam atingidos em cada nível do rio?")
    nivel = st.slider("Nível do Guaíba (m)", 3.0, 10.0, 5.3, 0.1, format="%.1f", key="nivel")
    cenario = cenarios_por_nivel(inct, nivel)
    atingidos = cenario.loc[cenario["affected_buildings"].gt(0)]
    st.caption(f"Cenário selecionado: {numero(nivel, 1)} m")

    pessoas, predios, bairros = st.columns(3)
    pessoas.metric("Pessoas afetadas (estimativa)", numero(cenario["affected_population"].sum()))
    predios.metric("Prédios afetados", numero(cenario["affected_buildings"].sum()))
    bairros.metric("Bairros atingidos", f"{len(atingidos)} de {len(cenario)}")
    st.info(
        "O INCT estima a população atingida supondo que os moradores se distribuem igualmente "
        "entre os prédios de cada bairro, inclusive os não residenciais. Os valores descrevem "
        "cenários simulados, sem função de previsão ou de contagem oficial."
    )

    curva_col, ranking_col = st.columns(2)
    with curva_col:
        st.subheader("População afetada por nível")
        figura = go.Figure(go.Scatter(
            x=curva.index, y=curva, mode="lines", line=dict(color=AZUL, width=3),
            hovertemplate="%{x:.1f} m<br>%{y:,.0f} pessoas<extra></extra>",
        ))
        figura.add_scatter(
            x=[nivel], y=[cenario["affected_population"].sum()], mode="markers",
            marker=dict(color=VERDE, size=10),
            hovertemplate="Nível escolhido: %{x:.1f} m<br>%{y:,.0f} pessoas<extra></extra>",
        )
        figura.add_vline(x=RECORDE, line_color=LARANJA, line_dash="dot")
        figura.add_scatter(
            x=[RECORDE], y=[populacao_no_recorde(curva)], mode="markers",
            marker=dict(color=LARANJA, size=8, symbol="diamond"),
            hovertemplate="Recorde de maio de 2024: 5,35 m<br>%{y:,.0f} pessoas (interpolação)<extra></extra>",
        )
        figura.update_xaxes(title="Nível do Guaíba (m)", dtick=1)
        figura.update_yaxes(title="Pessoas estimadas", rangemode="tozero", tickformat=",.0f")
        mostrar_grafico(figura, 335)
        st.caption("O losango laranja marca 5,35 m. A estimativa nesse ponto é interpolada entre 5,3 e 5,4 m.")

    with ranking_col:
        st.subheader("Bairros mais afetados")
        ordem = st.radio("Ordenar por", ["Pessoas estimadas", "% de prédios"], horizontal=True, key="ordem")
        coluna = {"Pessoas estimadas": "affected_population", "% de prédios": "percentage"}[ordem]
        ranking = atingidos.sort_values([coluna, "bairro"], ascending=[False, True]).head(10)
        tabela = pd.DataFrame({
            "Bairro": ranking["bairro"],
            "Pessoas": ranking["affected_population"].map(numero),
            "Prédios": ranking["affected_buildings"].map(numero),
            "% de prédios": ranking["percentage"].map(lambda x: f"{numero(x, 1)}%"),
        })
        st.dataframe(tabela, hide_index=True, use_container_width=True)
        st.caption("O ranking mostra até dez bairros. Um bairro é atingido quando tem ao menos um prédio afetado.")

    malha = ler_malha()
    if malha is not None:
        mostrar_mapa(cenario, malha)

    st.subheader("Percentual de prédios afetados por bairro")
    por_percentual = atingidos.sort_values(["percentage", "bairro"], ascending=[False, True])
    figura = barras_percentuais(
        por_percentual["bairro"], por_percentual["percentage"], AZUL,
        detalhes=por_percentual[["affected_buildings", "total_buildings"]].to_numpy(),
        texto_hover="<br>%{customdata[0]:,.0f} de %{customdata[1]:,.0f} prédios",
    )
    mostrar_grafico(figura, max(340, 25 * len(por_percentual) + 62))
    st.caption(
        f"Fonte: [INCT SiMAI]({FONTE_INCT}), JSON da simulação fornecido à equipe. "
        "Prédios: OpenStreetMap. População: Censo 2022/IBGE."
    )


def barras_peers(linhas: pd.DataFrame, cores) -> go.Figure:
    return barras_percentuais(
        linhas["categoria"], linhas["valor"], cores,
        erro=(linhas["ic95_sup"].clip(upper=100) - linhas["valor"]).clip(lower=0),
        erro_negativo=(linhas["valor"] - linhas["ic95_inf"]).clip(lower=0),
        detalhes=linhas["cv_pct"],
        texto_hover="<br>CV: %{customdata:.1f}%",
    )


def mostrar_renda(taxas: pd.DataFrame, fonte: str) -> None:
    st.subheader("Impactos e respostas por faixa de renda")
    indicador = st.selectbox("Indicador", list(INDICADORES_RENDA), key="indicador")
    tabela, trecho, universo = INDICADORES_RENDA[indicador]
    dados = taxas_do_indicador(taxas, tabela, trecho)
    faixas = dados.loc[CLASSES_RENDA]
    valores = faixas["taxa_pct"]
    margem = 1.96 * valores * faixas["cv_pct"] / 100
    total = dados.at["Total", "taxa_pct"]
    figura = go.Figure(go.Bar(
        x=CLASSES_RENDA, y=valores, marker_color=VERDE,
        error_y=dict(
            array=margem.clip(upper=100 - valores), arrayminus=margem.clip(upper=valores),
            thickness=1.3, color=CINZA,
        ),
        customdata=faixas["cv_pct"],
        hovertemplate="%{x}<br>%{y:.1f}%<br>CV do numerador: %{customdata:.1f}%<extra></extra>",
    ))
    figura.add_hline(y=total, line_dash="dot", line_color=LARANJA)
    figura.update_xaxes(title="Renda domiciliar mensal", automargin=True)
    figura.update_yaxes(title="Percentual", ticksuffix="%", range=[0, 100])
    mostrar_grafico(figura, 350)
    st.caption(
        f"{universo} Linha pontilhada: total da pesquisa ({numero(total, 1)}%). "
        f"As barras de erro aproximam o IC de 95% usando o CV do numerador. "
        f"Fonte: [PEERS/IBGE, Tabela {tabela}]({fonte})."
    )


def mostrar_ocorrencias(peers: pd.DataFrame, fonte: str) -> None:
    st.subheader("Ocorrências nos domicílios e no entorno")
    grupos = {
        "No domicílio": "Tipos de ocorrências causadas pelas enchentes no domicílio",
        "No bairro ou em ruas próximas": "Tipos de impactos causados pelas enchentes no bairro ou ruas próximas",
    }
    escolha = st.radio("Local da ocorrência", list(grupos), horizontal=True, key="ocorrencias")
    tabela = percentuais_da_tabela(peers, 6)
    linhas = tabela.loc[tabela["grupo"].eq(grupos[escolha])].sort_values("valor", ascending=False).copy()
    linhas["categoria"] = linhas["categoria"].str.replace(r"\s*\(.*\)", "", regex=True).str.rstrip(" .,")
    rotulos_curtos = {
        "Danos ou perda de móveis, eletrodomésticos, equipamentos de trabalho, aparelhos eletrônicos ou outro bem de alto valor":
            "Danos ou perda de bens",
    }
    linhas["categoria"] = linhas["categoria"].replace(rotulos_curtos)
    mostrar_grafico(barras_peers(linhas, AZUL), 400)
    st.caption(
        "Percentual dos domicílios da área atingida. A pergunta admite múltiplas respostas. "
        f"As barras de erro mostram IC de 95% aproximados. Fonte: [PEERS/IBGE, Tabela 6]({fonte})."
    )


def mostrar_deslocamento(peers: pd.DataFrame, fonte: str) -> None:
    st.subheader("Onde os moradores passaram a noite")
    tabela = percentuais_da_tabela(peers, 11)
    linhas = tabela.loc[tabela["categoria"].ne("Total")].sort_values("valor", ascending=False)
    cores = [AZUL_CLARO if alto else AZUL for alto in linhas["cv_alto"]]
    mostrar_grafico(barras_peers(linhas, cores), 300)
    st.caption(
        "Entre os domicílios com alguém que precisou passar ao menos uma noite fora. "
        "As barras claras indicam maior incerteza (coeficiente de variação acima de 15%). "
        f"Fonte: [PEERS/IBGE, Tabela 11]({fonte})."
    )


def mostrar_ligacao(inct: pd.DataFrame, curva: pd.Series, peers: pd.DataFrame, fonte: str) -> None:
    st.subheader("Maio de 2024 na simulação e na pesquisa")
    st.write("O recorde do Guaíba situa a simulação de Porto Alegre. A PEERS mostra ocorrências relatadas "
             "pelos moradores na área do RS abrangida pela pesquisa.")
    simulacao, pesquisa = st.columns([1, 2])
    with simulacao:
        st.markdown("**INCT SiMAI · Porto Alegre**")
        parcela = populacao_no_recorde(curva) / cenarios_por_nivel(inct, 3.0)["population"].sum() * 100
        st.metric("População estimada em prédios atingidos a 5,35 m", f"{numero(parcela, 1)}%")
        st.caption(
            f"Interpolação entre 5,3 e 5,4 m. Fonte: [INCT SiMAI]({FONTE_INCT}), "
            "JSON fornecido à equipe sem data de coleta informada."
        )
    with pesquisa:
        st.markdown("**PEERS/IBGE · Área atingida do RS**")
        impactos = impactos_do_evento(peers).sort_values(ascending=False)
        figura = barras_percentuais(impactos.index.to_series(), impactos, VERDE)
        mostrar_grafico(figura, 210)
        st.caption(f"Percentual dos domicílios da área pesquisada. Fonte: [PEERS/IBGE, Tabelas 1 e 6]({fonte}).")
    st.caption("Os percentuais descrevem universos diferentes: pessoas em Porto Alegre e domicílios "
               "na área pesquisada do RS. A relação entre as fontes é o evento de 2024.")


def mostrar_peers(inct: pd.DataFrame, curva: pd.Series) -> None:
    st.header("Impactos da enchente de 2024")
    st.write("O que aconteceu com os domicílios na área atingida e como os impactos variaram por faixa de renda?")
    peers = ler_csv("peers_longo.csv")
    taxas = ler_csv("peers_taxas_renda.csv")
    fonte, data = metadados_peers()
    st.caption(f"[PEERS/IBGE]({fonte}) · Dados coletados em {data}.")
    st.info("As estimativas vêm de uma pesquisa amostral por telefone na área atingida do RS. "
            "Os resultados destas tabelas são agregados para a área pesquisada.")
    renda, ocorrencias = st.columns(2)
    with renda:
        mostrar_renda(taxas, fonte)
    with ocorrencias:
        mostrar_ocorrencias(peers, fonte)
    mostrar_deslocamento(peers, fonte)
    mostrar_ligacao(inct, curva, peers, fonte)


def main() -> None:
    st.set_page_config(page_title="Enchentes no RS | INCT SiMAI", layout="wide")
    st.title("Enchentes no Rio Grande do Sul")
    inct = ler_csv("inct_longo_limpo.csv")
    curva = curva_populacao(inct)
    simulacao, pesquisa = st.tabs(["Simulação do Guaíba", "Enchente de 2024"])
    with simulacao:
        simular(inct, curva)
    with pesquisa:
        mostrar_peers(inct, curva)


if __name__ == "__main__":
    main()
