from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

# Get DB URL from environment (Render / PythonAnywhere / local)
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    # Example: postgresql://user:pass@host:port/dbname on Render
    engine = create_engine(DATABASE_URL, echo=False, future=True)
else:
    # Fallback to local SQLite file for development
    db_path = os.path.join(os.path.dirname(__file__), "webhooks.db")
    engine = create_engine(f"sqlite:///{db_path}", echo=False, future=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

def init_db():
    from models import Base
    Base.metadata.create_all(bind=engine)