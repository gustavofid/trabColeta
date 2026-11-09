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
| Leonardo Fagundes | _(usuário)_ |
| Leonardo Mallet | _(usuário)_ |
| Samuel Bitdinger | _(usuário)_ |

## Status

- [x] **Fase 1 – Levantamento de bases** (28/10): [`relatorios/base_dados.pdf`](relatorios/base_dados.pdf)
- [ ] Fase 2 – Dados limpos e EDA (09/11)
- [ ] Fase 3 – Protótipo do dashboard (16/11)
- [ ] Versão final (24/11)

Link do dashboard: _a publicar (Streamlit Community Cloud)_

## Bases de dados

| Base | Uso | Coleta |
|---|---|---|
| Simulação de inundação por bairro – INCT SiMAI (`data.json`) | Tela 1 | Arquivo fornecido pelo INCT |
| PEERS – Pesquisa Especial sobre as Enchentes de 2024 no RS (IBGE), Tabelas 1 a 21 (`dados/originais/peers/Abrangencia_xlsx/`) | Tela 2 | Download automatizado do FTP do IBGE (`scripts/coleta_peers.py`) |

Detalhes, licenças e justificativas em [`relatorios/base_dados.pdf`](relatorios/base_dados.pdf).

## Como rodar

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 1. Coleta da base externa (baixa só o que ainda não existe em dados/originais/)
python scripts/coleta_peers.py
```

Coloque o `data.json` do INCT em `dados/originais/inct/`.

## Estrutura

```
├── README.md
├── requirements.txt
├── dados/
│   ├── originais/      # dados como vieram (PEERS e INCT)
│   └── processados/    # dados limpos usados pelo dashboard
├── scripts/            # coleta e limpeza
├── notebooks/          # EDA
├── relatorios/         # base_dados.pdf, limpeza_dados.pdf, dashboard.pdf
├── docs/               # registro de uso de IA
└── app/                # código do dashboard
```

## Uso de ferramentas de IA

Todos os momentos em que usamos IA estão registrados em [`docs/uso_ia.md`](docs/uso_ia.md), como pede o enunciado.
