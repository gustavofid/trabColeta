# Análise de Dados de Enchentes do INCT SiMAI

Projeto extensionista da disciplina **Coleta, Preparação e Análise de Dados** (PUCRS, Profª Katherine Bianchini Esper de Vargas).

O objetivo é propor uma alternativa mais rápida e clara à ferramenta [Flood - INCT SiMAI](http://vhlab.com.br/INCT/floods/), com um dashboard de duas telas:

- **Tela 1 – Simulação do INCT:** se o Guaíba chegar a X metros (3,0 m a 10,0 m), quais bairros de Porto Alegre e quantas pessoas são afetados?
- **Tela 2 – Quem a enchente de 2024 atingiu, e como? A desigualdade de renda aparece nos danos e na recuperação?** Perfil dos domicílios e moradores afetados (renda, danos, deslocamento, trabalho, recuperação), a partir das Tabelas 1 a 21 da *Pesquisa Especial sobre as Enchentes de 2024 no Rio Grande do Sul* (PEERS/IBGE), ligadas à Tela 1 pelo evento de 2024 (nível recorde de 5,35 m).

> Os números do dashboard são **estimativas** (uma simulação e uma pesquisa amostral), não previsões nem contagens oficiais.

## Equipe

| Nome | GitHub |
|---|---|
| Gustavo Fidelis | [@gustavofid](https://github.com/gustavofid) |
| Leonardo Fagundes | [@leofwingert](https://github.com/leofwingert) |
| Leonardo Mallet | [@leomallet04](https://github.com/leomallet04) |
| Samuel Bitdinger | [@samuelb1t](https://github.com/samuelb1t) |

## Status

- [x] **Fase 1 – Levantamento de bases** (28/10): [`relatorios/base_dados.pdf`](relatorios/base_dados.pdf)
- [x] **Fase 2 – Dados limpos e EDA** (09/11): [`relatorios/limpeza_dados.pdf`](relatorios/limpeza_dados.pdf), [`notebooks/eda.ipynb`](notebooks/eda.ipynb), wireframes em [`relatorios/wireframes/`](relatorios/wireframes/)
- [ ] **Fase 3 – Dashboard** (24/11): telas em [`app/dashboard.py`](app/dashboard.py) e relatório em [PDF](relatorios/dashboard.pdf) e [LaTeX](relatorios/dashboard.tex). Publicação e entrega pendentes.
- [ ] Versão final (24/11)

Link do dashboard: _a publicar (Streamlit Community Cloud)_

## Bases de dados

| Base | Uso | Coleta |
|---|---|---|
| Simulação de inundação por bairro – INCT SiMAI (`data.json`) | Tela 1 | Arquivo fornecido pelo INCT |
| PEERS – Pesquisa Especial sobre as Enchentes de 2024 no RS (IBGE), Tabelas 1 a 21 (`dados/originais/peers/Abrangencia_xlsx/`) | Tela 2 | Download automatizado do FTP do IBGE (`scripts/coleta_peers.py`) |

Detalhes, licenças e justificativas em [`relatorios/base_dados.pdf`](relatorios/base_dados.pdf).

## Como rodar

As duas telas usam os CSVs tratados já incluídos no repositório. Na raiz do projeto:

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
python -m streamlit run app/dashboard.py
```

Para reproduzir a coleta, o tratamento e a análise exploratória, com o ambiente ativado:

```bash
# 1. Coleta da base externa (baixa só o que ainda não existe em dados/originais/)
python scripts/coleta_peers.py

# 2. Limpeza (gera os arquivos de dados/processados/)
python scripts/limpeza_inct.py     # precisa de dados/originais/inct/data.json
python scripts/limpeza_peers.py
python scripts/mapa_bairros.py     # precisa da malha em dados/originais/bairros/

# 3. Análise exploratória
jupyter notebook notebooks/eda.ipynb
```

| Arquivo processado | Conteúdo |
|---|---|
| `dados/processados/inct_longo_limpo.csv` | Simulação do INCT limpa, uma linha por nível e bairro (6.674 linhas) |
| `dados/processados/inct_correcoes.csv` | Cada valor corrigido: bairro, nível, regra, antes e depois |
| `dados/processados/peers_longo.csv` | As 21 tabelas da PEERS em formato longo, com CV e IC 95% |
| `dados/processados/peers_taxas_renda.csv` | Taxas por classe de renda usadas na Tela 2 |
| `dados/processados/bairros.geojson` | Contornos dos bairros usados no mapa da Tela 1 |

A malha de bairros vem do [servidor de mapas da Prefeitura](https://gis-smamus.portoalegre.rs.gov.br/server/rest/services/01_PUBLICACOES/bairros_2016/MapServer) (limites da Lei 12.112/2016) e fica salva em `dados/originais/bairros/bairros_2016.geojson`.

## Relatório do dashboard

Com uma distribuição LaTeX instalada, rode na raiz do projeto:

```bash
pdflatex -interaction=nonstopmode -halt-on-error -output-directory=relatorios relatorios/dashboard.tex
```

## Estrutura

```
├── README.md
├── requirements.txt
├── dados/
│   ├── originais/      # dados como vieram (PEERS e INCT)
│   └── processados/    # dados limpos usados pelo dashboard
├── scripts/            # coleta e limpeza
├── notebooks/          # EDA
├── relatorios/         # relatórios das fases, dashboard.tex e PDF compilado
├── docs/               # registro de uso de IA
└── app/                # código do dashboard
```

## Uso de ferramentas de IA

Todos os momentos em que usamos IA estão registrados em [`docs/uso_ia.md`](docs/uso_ia.md), como pede o enunciado.
