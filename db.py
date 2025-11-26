from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

db_path = os.path.join(os.path.dirname(__file__), "webhooks.db")
print(f"Using database file at: {db_path}")

engine = create_engine(f"sqlite:///{db_path}", echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

def init_db():
    from models import Base
    Base.metadata.create_all(bind=engine)
