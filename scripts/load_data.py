import os

import geopandas as gpd
import pandas as pd
from dotenv import load_dotenv
from geoalchemy2 import Geometry
from shapely.geometry import MultiPolygon, Polygon
from sqlalchemy import create_engine, text

IBGE_MALHAS_URL = (
    "https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/"
    "malhas_municipais/municipio_2018/Brasil/BR"
)
ESTADOS_URL = f"{IBGE_MALHAS_URL}/br_unidades_da_federacao.zip"
MUNICIPIOS_URL = f"{IBGE_MALHAS_URL}/br_municipios.zip"

FOCOS_WFS_URL = (
    "https://terrabrasilis.dpi.inpe.br/queimadas/geoserver/dados_abertos/ows"
    "?service=WFS&version=2.0.0&request=GetFeature"
    "&typeName=dados_abertos:focos_48h_br_todosats"
    "&outputFormat=application/json&srsName=EPSG:4674"
)

load_dotenv()

engine = create_engine(
    "mysql+pymysql://{user}:{pswd}@{host}:{port}/{db}".format(
        user=os.getenv("MARIADB_USER"),
        pswd=os.getenv("MARIADB_PASSWORD"),
        host=os.getenv("HOST"),
        port=os.getenv("PORT"),
        db=os.getenv("MARIADB_DATABASE"),
    )
)


def _as_multipolygon(geometry: gpd.GeoSeries) -> gpd.GeoSeries:
    return geometry.apply(lambda g: MultiPolygon([g]) if isinstance(g, Polygon) else g)


def _to_nullable_numeric(df: pd.DataFrame, columns: list[str]) -> None:
    # Dados inválidos (como precipitação negativa) são convertidos para None, 
    # e colunas numéricas são convertidas para object dtype para permitir valores nulos.
    for col in columns:
        series = pd.to_numeric(df[col], errors="coerce")
        series = series.mask(series < 0)
        df[col] = series.astype(object).where(series.notna(), None)


def _table_is_empty(table: str) -> bool:
    with engine.connect() as conn:
        return conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar() == 0


def load_estados() -> None:
    if not _table_is_empty("estados"):
        print("estados already loaded, skipping")
        return

    estados = gpd.read_file(ESTADOS_URL)
    estados = estados.rename(
        columns={
            "NM_ESTADO": "nome",
            "NM_REGIAO": "regiao",
            "CD_GEOCUF": "codigo_ibge",
        }
    ).filter(items=["codigo_ibge", "nome", "regiao", "geometry"])
    estados["codigo_ibge"] = estados["codigo_ibge"].astype(int)
    estados["geometry"] = _as_multipolygon(estados["geometry"])

    estados.to_sql(
        name="estados",
        con=engine,
        if_exists="append",
        index=False,
        dtype={"geometry": Geometry(geometry_type="MULTIPOLYGON", srid=4674)},
    )
    print(f"loaded {len(estados)} estados")


def load_municipios() -> None:
    if not _table_is_empty("municipios"):
        print("municipios already loaded, skipping")
        return

    municipios = gpd.read_file(MUNICIPIOS_URL)
    municipios = municipios.rename(
        columns={"NM_MUNICIP": "nome", "CD_GEOCMU": "geocodigo_ibge"}
    ).filter(items=["nome", "geocodigo_ibge", "geometry"])
    municipios["geocodigo_ibge"] = municipios["geocodigo_ibge"].astype(int)
    municipios["geometry"] = _as_multipolygon(municipios["geometry"])

    # Municípios no IBGE tem o estado embutido no código IBGE, 
    # então podemos derivar o estado_id a partir do geocódigo.
    municipios["codigo_ibge"] = municipios["geocodigo_ibge"] // 100000
    estados = pd.read_sql("SELECT id AS estado_id, codigo_ibge FROM estados", con=engine)
    municipios = municipios.merge(estados, on="codigo_ibge", how="left").drop(columns=["codigo_ibge"])

    unmatched = municipios["estado_id"].isna()
    if unmatched.any():
        print(f"dropping {unmatched.sum()} municipios with no matching estado")
        municipios = municipios[~unmatched]
        
    municipios["estado_id"] = municipios["estado_id"].astype(int)

    municipios.to_sql(
        name="municipios",
        con=engine,
        if_exists="append",
        index=False,
        dtype={"geometry": Geometry(geometry_type="MULTIPOLYGON", srid=4674)},
    )
    print(f"loaded {len(municipios)} municipios")


def load_focos_de_fogo() -> None:
    focos = gpd.read_file(FOCOS_WFS_URL)
    focos = focos.rename(columns={"numero_dias_sem_chuva": "dias_sem_chuva"}).filter(
        items=[
            "id_foco_bdq",
            "municipio",
            "estado",
            "satelite",
            "data_hora_gmt",
            "data_pas",
            "bioma",
            "precipitacao",
            "dias_sem_chuva",
            "risco_fogo",
            "frp",
            "geometry",
        ]
    )
    focos["data_hora_gmt"] = focos["data_hora_gmt"].dt.tz_localize(None)
    focos["data_pas"] = focos["data_pas"].dt.date
    _to_nullable_numeric(focos, ["precipitacao", "dias_sem_chuva", "risco_fogo", "frp"])

    # Faz JOIN de municípios pelo nome
    municipios = pd.read_sql(
        """
        SELECT m.id AS municipio_id, m.nome AS municipio, e.nome AS estado
        FROM municipios m
        JOIN estados e ON e.id = m.estado_id
        """,
        con=engine,
    )
    focos = focos.merge(municipios, on=["municipio", "estado"], how="left").drop(
        columns=["municipio", "estado"]
    )

    unmatched = focos["municipio_id"].isna()
    if unmatched.any():
        print(f"dropping {unmatched.sum()} fire detections with no matching municipio")
        focos = focos[~unmatched]
    focos["municipio_id"] = focos["municipio_id"].astype(int)

    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE focos_de_fogo"))

    focos.to_sql(
        name="focos_de_fogo",
        con=engine,
        if_exists="append",
        index=False,
        dtype={"geometry": Geometry(geometry_type="POINT", srid=4674)},
    )
    print(f"loaded {len(focos)} focos_de_fogo")


if __name__ == "__main__":
    load_estados()
    load_municipios()
    load_focos_de_fogo()
