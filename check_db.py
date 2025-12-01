import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Group, Service, GroupService
import pandas as pd

DATABASE_URL = "postgresql://webhook_config_user:bw5bj1AQ2AuBMf59bhRS5NvPQm3MmAcm@dpg-d4lmlsje5dus73fstta0-a.oregon-postgres.render.com/webhook_config"  # or use os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

# def main():
#     session = SessionLocal()
#     try:
#         groups = session.query(Group).all()
#         print(groups)
#
#     finally:
#         session.close()
def main():
    session = SessionLocal()
    try:
        groups = session.query(Group).all()

        # Convert list of objects to a list of dictionaries
        data = [
            {k: v for k, v in vars(g).items() if not k.startswith('_')}
            for g in groups
        ]

        df = pd.DataFrame(data)
        print(df.to_string())  # to_string() ensures it prints the whole table

    finally:
        session.close()

if __name__ == "__main__":
    main()
