# mariadb-study

Estudo acadêmico simples sobre o MariaDB, explorando seus recursos de **banco de dados relacional** e de **dados espaciais** (tipos geométricos, índices espaciais e funções `ST_*`) a partir de um cenário real: o cruzamento entre estados, municípios e focos de queimada no Brasil.

## Modelo de dados

O banco é composto por três tabelas relacionadas entre si por chave estrangeira:

```
estados (1) ──< municipios (1) ──< focos_de_fogo
```

- **`estados`** — unidades federativas do Brasil, com nome, região e a geometria (polígono) do seu território.
- **`municipios`** — municípios brasileiros, cada um associado ao seu estado (`estado_id`), com nome, código IBGE e geometria do território.
- **`focos_de_fogo`** — detecções de queimada por satélite, cada uma associada ao município (`municipio_id`) onde ocorreu, com data/hora, satélite, bioma e indicadores como risco de fogo e potência radiativa do fogo (FRP).

Todas as tabelas possuem colunas de geometria (`MULTIPOLYGON` ou `POINT`) com índice espacial (`SPATIAL INDEX`), permitindo consultas como "quais focos de incêndio caem dentro desta área" usando funções como `ST_Intersects`.

O schema fica em [`sql/01_schema.sql`](sql/01_schema.sql).

## Fontes de dados

- **Estados e municípios**: malhas territoriais do IBGE (ano-base 2018) — [`br_unidades_da_federacao.zip`](https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/malhas_municipais/municipio_2018/Brasil/BR/br_unidades_da_federacao.zip) e [`br_municipios.zip`](https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/malhas_municipais/municipio_2018/Brasil/BR/br_municipios.zip).
- **Focos de queimada**: serviço WFS do programa Queimadas do INPE, camada `focos_48h_br_todosats` (últimas 48h de detecções por satélite).

Os dados são baixados e tratados automaticamente por [`scripts/load_data.py`](scripts/load_data.py) — não é necessário baixar nada manualmente.

## Como executar

Pré-requisitos: Docker e Docker Compose.

```bash
cp .env.example .env   # ajuste as credenciais se quiser
docker compose up --build
```

Isso sobe o container do MariaDB (aplicando o schema automaticamente na primeira execução) e, assim que o banco estiver saudável, executa o container `loader`, que popula `estados` e `municipios` (uma única vez) e atualiza `focos_de_fogo` a cada execução, já que a fonte é uma janela móvel das últimas 48h.

Para recomeçar do zero (por exemplo, após alterar o schema):

```bash
docker compose down -v
docker compose up --build
```

## Notebook de demonstração

[`notebooks/demo.ipynb`](notebooks/demo.ipynb) conecta ao banco e exibe um mapa interativo (via [leafmap](https://leafmap.org/)) onde é possível desenhar uma área de interesse. A partir da área desenhada, o notebook executa uma única consulta SQL que junta `focos_de_fogo`, `municipios` e `estados` pelas chaves estrangeiras, filtrando espacialmente com `ST_Intersects`, e exibe os focos encontrados de volta no mapa com seus atributos de município e estado.

## Estrutura do projeto

```
sql/                  schema do banco (executado automaticamente pelo MariaDB)
scripts/
  load_data.py         script de ingestão (IBGE + INPE) executado pelo container `loader`
  Dockerfile           imagem do container `loader`
notebooks/
  demo.ipynb           notebook de demonstração com mapa interativo
docker-compose.yml     orquestração do MariaDB e do loader
```
