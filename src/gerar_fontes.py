import os
import numpy as np
import pandas as pd
from config import RAIZ

rng = np.random.default_rng(42)
os.makedirs(f"{RAIZ}/data/raw", exist_ok=True)

# ---- Fonte 3: cidades (dados de apoio) ----
cidades = pd.DataFrame({"cidade": ["Macapá", "Santana", "Belém", "Manaus"],
                        "estado": ["AP", "AP", "PA", "AM"],
                        "populacao": [442933, 107618, 1303403, 2063547]})
cidades.to_csv(f"{RAIZ}/data/raw/cidades.csv", index=False)

# ---- Fonte 1: clientes (CSV) ----
n = 600
cli = pd.DataFrame({
    "id_cliente": np.arange(1, n + 1),
    "email": [f"cliente{i}@exemplo.com" for i in range(1, n + 1)],
    "idade": rng.integers(18, 70, n).astype(float),
    "cidade": rng.choice(cidades["cidade"].to_numpy(), n),
    "canal": rng.choice(["Site", "App", "Loja"], n),
    "data_cadastro": (pd.Timestamp("2024-01-01")
                      + pd.to_timedelta(rng.integers(0, 365, n), unit="D")).strftime("%Y-%m-%d"),
})
# sujeira proposital
i = rng.choice(n, 70, replace=False)
cli.loc[i, "data_cadastro"] = pd.to_datetime(cli.loc[i, "data_cadastro"]).dt.strftime("%d/%m/%Y")
i = rng.choice(n, 120, replace=False)
cli.loc[i, "cidade"] = cli.loc[i, "cidade"].apply(lambda s: rng.choice([s.upper(), s.lower(), f"  {s} "]))
i = rng.choice(n, 80, replace=False)
cli.loc[i, "email"] = cli.loc[i, "email"].str.upper()
cli.loc[rng.choice(n, 40, replace=False), "idade"] = np.nan
cli.loc[rng.choice(n, 8, replace=False), "idade"] = -5
cli.loc[rng.choice(n, 40, replace=False), "cidade"] = np.nan
cli = pd.concat([cli, cli.sample(30, random_state=1)]).sample(frac=1, random_state=1)
cli.to_csv(f"{RAIZ}/data/raw/clientes.csv", index=False)

# ---- Fonte 2: pedidos (JSON) ----
propensao = rng.gamma(2, 1, n)   # clientes mais "ativos" compram mais
pedidos, pid = [], 1
for idc, p in zip(range(1, n + 1), propensao):
    for _ in range(rng.poisson(p * 1.5)):
        pedidos.append({
            "id_pedido": pid, "id_cliente": idc,
            "data_pedido": (pd.Timestamp("2025-01-01")
                            + pd.Timedelta(days=int(rng.integers(0, 365)))).strftime("%Y-%m-%d"),
            "valor": round(float(rng.gamma(4, 40)), 2),
            "categoria": str(rng.choice(["Pizza", "Lanche", "Japonesa", "Saudável"]))})
        pid += 1
ped = pd.DataFrame(pedidos)
ped["valor"] = ped["valor"].astype(object)
i = rng.choice(len(ped), 60, replace=False)
ped.loc[i, "valor"] = ped.loc[i, "valor"].apply(lambda v: f"R$ {v:.2f}".replace(".", ","))
ped.loc[rng.choice(len(ped), 8, replace=False), "valor"] = 50000.0     # outliers
ped.loc[rng.choice(len(ped), 15, replace=False), "valor"] = None       # ausentes
ped = pd.concat([ped, ped.sample(40, random_state=2)], ignore_index=True)   # duplicatas
ped.loc[ped.index[-5:], "id_cliente"] = 9999                           # cliente inexistente
ped.to_json(f"{RAIZ}/data/raw/pedidos.json", orient="records", force_ascii=False)

print("clientes:", len(cli), "| pedidos:", len(ped), "| cidades:", len(cidades))
