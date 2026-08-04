USE mariadb_geo;

CREATE TABLE estados (
    id TINYINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    codigo_ibge TINYINT UNSIGNED NOT NULL UNIQUE,
    nome VARCHAR(100) NOT NULL,
    regiao VARCHAR(20) NOT NULL,
    geometry MULTIPOLYGON NOT NULL,
    srid INT NOT NULL DEFAULT 4674,
    SPATIAL INDEX idx_geometry (geometry)
);

CREATE TABLE municipios (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    geocodigo_ibge INT UNSIGNED NOT NULL UNIQUE,
    estado_id TINYINT UNSIGNED NOT NULL,
    geometry MULTIPOLYGON NOT NULL,
    srid INT NOT NULL DEFAULT 4674,
    FOREIGN KEY (estado_id) REFERENCES estados(id),
    SPATIAL INDEX idx_geometry (geometry)
);

CREATE TABLE focos_de_fogo (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    id_foco_bdq BIGINT UNSIGNED NOT NULL UNIQUE,
    municipio_id INT UNSIGNED NOT NULL,
    satelite VARCHAR(50) NOT NULL,
    data_hora_gmt DATETIME NOT NULL,
    data_pas DATE,
    bioma VARCHAR(50),
    precipitacao DECIMAL(6, 2),
    dias_sem_chuva SMALLINT,
    risco_fogo DECIMAL(4, 3),
    frp DECIMAL(8, 2),
    geometry POINT NOT NULL,
    srid INT NOT NULL DEFAULT 4674,
    FOREIGN KEY (municipio_id) REFERENCES municipios(id),
    SPATIAL INDEX idx_geometry (geometry)
);
