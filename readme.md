# Projeto Integrador: Previsão de Recompra de Clientes

## Descrição
Pipeline end-to-end de Engenharia de Dados e Machine Learning:
**Fontes (CSV + JSON) → PostgreSQL → ETL Python → Features (SQL) → Modelo → Métricas.**
Problema: prever se um cliente fará nova compra após uma data de corte (classificação binária).

## Fontes de dados
| Fonte | Formato | Conteúdo |
|---|---|---|
| clientes.csv | CSV | cadastro (id, email, idade, cidade, canal, data de cadastro) |
| pedidos.json | JSON | histórico de compras |
| cidades.csv | CSV | dados de apoio (estado, população) |

As fontes são geradas por `src/gerar_fontes.py` com sujeira proposital (duplicados, nulos, formatos mistos, outliers, cliente inexistente).

## Modelagem (PostgreSQL)
```
dim_cidade (id_cidade PK, cidade, estado, populacao)
dim_cliente (id_cliente PK, email, idade, canal, data_cadastro, id_cidade FK)
fato_pedido (id_pedido PK, id_cliente FK, data_pedido, valor, categoria)
```
DDL com PKs, FKs, CHECKs e índices em `sql/schema.sql`.

## Estrutura do repositório
```
projeto-integrador/
├── README.md
├── requirements.txt
├── docker-compose.yml
├── data/raw/            fontes brutas
├── data/processed/      dataset de treino
├── sql/schema.sql       criação das tabelas
├── sql/features.sql     features calculadas no banco
├── src/config.py        configuração (conexão, data de corte)
├── src/gerar_fontes.py  coleta (gera as 3 fontes)
├── src/etl.py           Extract, Transform, Load
├── src/treinar.py       features, modelos, métricas e .pkl
├── notebooks/           notebook de EDA e resultados
├── models/              modelo_final.pkl, metricas.json, comparacao_modelos.csv
└── docs/                gráficos e log de qualidade
```

## Como executar
```bash
pip install -r requirements.txt
docker compose up -d                 # PostgreSQL
python src/gerar_fontes.py           # 1. coleta
python src/etl.py                    # 2. ETL e carga no PostgreSQL
python src/treinar.py                # 3. features, treino, avaliação e .pkl
```
Depois, abra `notebooks/projeto_integrador.ipynb`.
A conexão usa a variável `DB_URL` (padrão: `postgresql+psycopg2://ml:ml123@localhost:5432/projeto_integrador`).

## Qualidade dos dados (ETL)
| Etapa | Antes | Depois |
|---|---|---|
| Clientes | 630 | 600 |
| Pedidos | 1818 | 1763 |

Correções: 30 clientes duplicados removidos; 40 cidades nulas → "Desconhecida"; 8 idades inválidas e 48 nulas → mediana; 35 pedidos duplicados removidos; 60 valores "R$" convertidos; 15 pedidos sem valor/data removidos; 51 outliers limitados pelo IQR; 5 pedidos de cliente inexistente removidos (integridade referencial).

## Decisões técnicas
- **Data de corte (2025-09-01):** features usam só pedidos anteriores e o target usa compras posteriores, evitando vazamento.
- **Features em SQL:** agregações calculadas no PostgreSQL.
- **Outliers limitados (clip)** em vez de removidos, para preservar linhas.
- **Métricas:** ROC-AUC e F1, não só accuracy; baseline (Dummy) como referência.
- **Escolha do modelo** pelo ROC-AUC em validação cruzada, sem usar o teste.

## Resultados
Target positivo: 54,5%. Treino 480 | Teste 120.

| Modelo | Accuracy | Precision | Recall | F1 | ROC-AUC | ROC-AUC (CV5) |
|---|---|---|---|---|---|---|
| Baseline | 0,542 | 0,542 | 1,000 | 0,703 | 0,500 | 0,500 |
| **LogisticRegression** | **0,658** | **0,722** | 0,600 | 0,655 | **0,684** | **0,638** |
| RandomForest | 0,600 | 0,605 | 0,754 | 0,671 | 0,618 | 0,614 |
| GradientBoosting | 0,592 | 0,611 | 0,677 | 0,642 | 0,609 | 0,636 |

Modelo escolhido: **Regressão Logística**. Todos superam o baseline em ROC-AUC. O F1 do baseline é enganoso (prevê sempre a classe majoritária).

## Limitações e próximos passos
- Amostra pequena e dados sintéticos; diferenças entre modelos podem estar dentro da variação.
- Mediana de idade e limite de outliers calculados com todos os dados no ETL.
- Próximos passos: dados reais, ajuste de hiperparâmetros, API com FastAPI.

## Equipe
- Francineia: ETL, modelagem PostgreSQL, modelagem e documentação
