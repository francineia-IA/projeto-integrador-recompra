DROP TABLE IF EXISTS fato_pedido CASCADE;
DROP TABLE IF EXISTS dim_cliente CASCADE;
DROP TABLE IF EXISTS dim_cidade CASCADE;

CREATE TABLE dim_cidade (
    id_cidade  SERIAL PRIMARY KEY,
    cidade     VARCHAR(60) UNIQUE NOT NULL,
    estado     CHAR(2),
    populacao  INT
);

CREATE TABLE dim_cliente (
    id_cliente     INT PRIMARY KEY,
    email          VARCHAR(120),
    idade          INT CHECK (idade BETWEEN 18 AND 100),
    canal          VARCHAR(20),
    data_cadastro  DATE,
    id_cidade      INT REFERENCES dim_cidade(id_cidade)
);

CREATE TABLE fato_pedido (
    id_pedido    INT PRIMARY KEY,
    id_cliente   INT NOT NULL REFERENCES dim_cliente(id_cliente),
    data_pedido  DATE NOT NULL,
    valor        NUMERIC(10,2) CHECK (valor > 0),
    categoria    VARCHAR(30)
);

CREATE INDEX idx_pedido_cliente ON fato_pedido(id_cliente);
CREATE INDEX idx_pedido_data ON fato_pedido(data_pedido);
