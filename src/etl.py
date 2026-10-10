import json
import numpy as np
import pandas as pd
from sqlalchemy import create_engine
from config import RAIZ, DB_URL

RAW = f"{RAIZ}/data/raw"


def para_numero(s):
    """'R$ 45,90' -> 45.90 (texto inválido vira NaN)."""
    return pd.to_numeric(s.astype(str).str.replace("R$", "", regex=False)
                         .str.replace(",", ".", regex=False).str.strip(), errors="coerce")


def data_mista(s):
    """Aceita AAAA-MM-DD e DD/MM/AAAA."""
    return pd.to_datetime(s, format="%Y-%m-%d", errors="coerce").fillna(
        pd.to_datetime(s, format="%d/%m/%Y", errors="coerce"))


# ---------------- EXTRACT ----------------
def extract():
    cli = pd.read_csv(f"{RAW}/clientes.csv")
    ped = pd.read_json(f"{RAW}/pedidos.json", dtype=False, convert_dates=False)
    cid = pd.read_csv(f"{RAW}/cidades.csv")
    print(f"[EXTRACT] clientes={len(cli)} | pedidos={len(ped)} | cidades={len(cid)}")
    return cli, ped, cid


# ---------------- TRANSFORM ----------------
def transform(cli, ped, cid):
    log = {"entrada: clientes": len(cli), "entrada: pedidos": len(ped)}

    # cidades
    cid = cid.copy()
    cid["cidade"] = cid["cidade"].str.strip().str.title()
    cid = pd.concat([cid, pd.DataFrame([{"cidade": "Desconhecida", "estado": None, "populacao": None}])],
                    ignore_index=True)
    cid["populacao"] = cid["populacao"].astype("Int64")

    # clientes
    c = cli.copy()
    log["clientes: duplicados removidos"] = int(c.duplicated().sum())
    c = c.drop_duplicates("id_cliente")
    log["clientes: cidades nulas -> 'Desconhecida'"] = int(c["cidade"].isna().sum())
    c["cidade"] = c["cidade"].str.strip().str.title().fillna("Desconhecida")
    c["email"] = c["email"].str.lower().str.strip()
    c["canal"] = c["canal"].str.strip().str.title()
    c["data_cadastro"] = data_mista(c["data_cadastro"])
    inval = ~c["idade"].between(18, 100) & c["idade"].notna()
    log["clientes: idades inválidas"] = int(inval.sum())
    c.loc[inval, "idade"] = np.nan
    log["clientes: idades nulas (preenchidas com mediana)"] = int(c["idade"].isna().sum())
    c["idade"] = c["idade"].fillna(c["idade"].median()).astype(int)
    c = c.dropna(subset=["data_cadastro"]).copy()

    # pedidos
    p = ped.copy()
    log["pedidos: duplicados removidos"] = int(p.duplicated().sum())
    p = p.drop_duplicates()
    log["pedidos: valores com 'R$' convertidos"] = int(p["valor"].astype(str).str.contains("R\\$").sum())
    p["valor"] = para_numero(p["valor"])
    p["data_pedido"] = data_mista(p["data_pedido"])
    n0 = len(p)
    p = p.dropna(subset=["valor", "data_pedido"])
    p = p[p["valor"] > 0]
    log["pedidos: sem valor/data removidos"] = n0 - len(p)
    q1, q3 = p["valor"].quantile([.25, .75])
    lim = q3 + 1.5 * (q3 - q1)
    log["pedidos: outliers limitados"] = int((p["valor"] > lim).sum())
    p["valor"] = p["valor"].clip(upper=lim)
    n0 = len(p)
    p = p[p["id_cliente"].isin(c["id_cliente"])]
    log["pedidos: cliente inexistente removidos (integridade)"] = n0 - len(p)
    p = p.drop_duplicates("id_pedido").copy()

    log["saída: clientes"] = len(c)
    log["saída: pedidos"] = len(p)
    print("[TRANSFORM]")
    for k, v in log.items():
        print(f"   {k}: {v}")
    return c, p, cid, log


# ---------------- LOAD ----------------
def load(c, p, cid):
    eng = create_engine(DB_URL)
    with open(f"{RAIZ}/sql/schema.sql", encoding="utf-8") as f, eng.begin() as con:
        con.exec_driver_sql(f.read())

    cid.to_sql("dim_cidade", eng, if_exists="append", index=False)
    mapa = pd.read_sql("SELECT id_cidade, cidade FROM dim_cidade", eng).set_index("cidade")["id_cidade"]

    c = c.assign(id_cidade=c["cidade"].map(mapa)).drop(columns="cidade")
    c.to_sql("dim_cliente", eng, if_exists="append", index=False)

    p = p.copy()
    p["data_pedido"] = p["data_pedido"].dt.date
    p[["id_pedido", "id_cliente", "data_pedido", "valor", "categoria"]].to_sql(
        "fato_pedido", eng, if_exists="append", index=False)

    for t in ["dim_cidade", "dim_cliente", "fato_pedido"]:
        n = pd.read_sql(f"SELECT COUNT(*) AS n FROM {t}", eng).iloc[0, 0]
        print(f"[LOAD] {t}: {n} linhas")


if __name__ == "__main__":
    cli, ped, cid = extract()
    c, p, cid, log = transform(cli, ped, cid)
    load(c, p, cid)
    with open(f"{RAIZ}/docs/log_qualidade.json", "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)
