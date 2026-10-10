import os

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_URL = os.getenv("DB_URL", "postgresql+psycopg2://ml:ml123@localhost:5432/projeto_integrador")
DATA_CORTE = "2025-09-01"
