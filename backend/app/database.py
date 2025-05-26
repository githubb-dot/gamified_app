# Database setup for "Alone, I Level Up" App

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# DATABASE_URL = "postgresql://user:password@host:port/database"
# For MVP, we might use SQLite for simplicity if PostgreSQL setup is delayed,
# but the spec points to PostgreSQL. We'll use an environment variable.
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:mysecretpassword@localhost:5432/alone_i_level_up_db")
# Fallback to SQLite for easier local testing if POSTGRES_HOST is not set
if "localhost" in DATABASE_URL and not os.getenv("POSTGRES_HOST"): # A simple check if we are in a local dev without explicit PG
    DATABASE_URL = "sqlite:///./alone_i_level_up.db"
    engine = create_engine(
        DATABASE_URL, connect_args={"check_same_thread": False} # Needed for SQLite
    )
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Function to create all tables (call this once at app startup if not using Alembic initially)
# In a production setup, Alembic would handle migrations.
def create_db_and_tables():
    # Import all models here to ensure they are registered with Base
    # This is a simplified way; Alembic is preferred for schema management.
    from models import User, Goal, Quest, Stat, XPEvent, Report # Ensure all models are imported
    Base.metadata.create_all(bind=engine)

