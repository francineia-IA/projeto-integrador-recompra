import json
import joblib
import pandas as pd
from sqlalchemy import create_engine
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from config import RAIZ, DB_URL, DATA_CORTE

NUM = ["idade", "populacao", "dias_cadastro", "qtd_pedidos", "total_gasto",
       "ticket_medio", "dias_desde_ultimo", "categorias_distintas"]
CAT = ["canal", "cidade"]


def montar_dataset():
    """Features calculadas no PostgreSQL (só pedidos ANTES da data de corte);
    target = 1 se o cliente comprou DEPOIS do corte."""
    eng = create_engine(DB_URL)
    sql = open(f"{RAIZ}/sql/features.sql", encoding="utf-8").read().replace("{corte}", DATA_CORTE)
    X = pd.read_sql(sql, eng)
    y = pd.read_sql(f"SELECT DISTINCT id_cliente, 1 AS recompra FROM fato_pedido "
                    f"WHERE data_pedido >= DATE '{DATA_CORTE}'", eng)
    df = X.merge(y, on="id_cliente", how="left").fillna({"recompra": 0})
    df["populacao"] = df["populacao"].astype(float)
    df["populacao"] = df["populacao"].fillna(df["populacao"].median())
    df.to_csv(f"{RAIZ}/data/processed/dataset_treino.csv", index=False)
    return df


def novo_pipe(modelo):
    prep = ColumnTransformer([("num", StandardScaler(), NUM),
                              ("cat", OneHotEncoder(handle_unknown="ignore"), CAT)])
    return Pipeline([("prep", prep), ("model", modelo)])


if __name__ == "__main__":
    df = montar_dataset()
    X, y = df[NUM + CAT], df["recompra"].astype(int)
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)
    print(f"Target positivo: {y.mean():.1%} | treino: {Xtr.shape} | teste: {Xte.shape}")

    modelos = {
        "Baseline": DummyClassifier(strategy="prior"),
        "LogisticRegression": LogisticRegression(max_iter=1000, class_weight="balanced"),
        "RandomForest": RandomForestClassifier(n_estimators=300, random_state=42, class_weight="balanced"),
        "GradientBoosting": GradientBoostingClassifier(random_state=42),
    }
    cv = StratifiedKFold(5, shuffle=True, random_state=42)
    res, ajust = [], {}
    for nome, m in modelos.items():
        pipe = novo_pipe(m).fit(Xtr, ytr)
        ajust[nome] = pipe
        pred, proba = pipe.predict(Xte), pipe.predict_proba(Xte)[:, 1]
        res.append({"modelo": nome,
                    "accuracy": accuracy_score(yte, pred),
                    "precision": precision_score(yte, pred, zero_division=0),
                    "recall": recall_score(yte, pred, zero_division=0),
                    "f1": f1_score(yte, pred, zero_division=0),
                    "roc_auc": roc_auc_score(yte, proba),
                    "roc_auc_cv5": cross_val_score(pipe, Xtr, ytr, cv=cv, scoring="roc_auc").mean()})
    tab = pd.DataFrame(res).set_index("modelo").round(3)
    print(tab)

    melhor = tab.drop("Baseline")["roc_auc_cv5"].idxmax()
    print("Modelo escolhido:", melhor)
    joblib.dump(ajust[melhor], f"{RAIZ}/models/modelo_final.pkl")
    tab.to_csv(f"{RAIZ}/models/comparacao_modelos.csv")
    with open(f"{RAIZ}/models/metricas.json", "w") as f:
        json.dump({"modelo": melhor, **tab.loc[melhor].to_dict()}, f, indent=2)
