from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

# Try to get DB URL from the environment (Render / PythonAnywhere / local .env)
DATABASE_URL = os.getenv("postgresql://webhook_config_user:bw5bj1AQ2AuBMf59bhRS5NvPQm3MmAcm@dpg-d4lmlsje5dus73fstta0-a/webhook_config")

if DATABASE_URL:
    # Example: postgres://user:pass@host:port/dbname on Render
    engine = create_engine(DATABASE_URL, echo=False, future=True)
else:
    # Fallback to local SQLite file for development
    db_path = os.path.join(os.path.dirname(__file__), "webhooks.db")
    engine = create_engine(f"sqlite:///{db_path}", echo=False, future=True)


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db():
    from models import Base

    Base.metadata.create_all(bind=engine)