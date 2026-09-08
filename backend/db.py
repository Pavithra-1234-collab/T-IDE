import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine


load_dotenv(Path(__file__).with_name(".env"))

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
	raise ValueError("DATABASE_URL is not set in the .env file")

engine = create_engine(DATABASE_URL)

__all__ = ["engine"]

