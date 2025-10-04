# Import necessary components from SQLAlchemy.
# create_engine: Used to establish a connection to the database.
# declarative_base: A factory function that produces a base class for declarative class definitions.
# sessionmaker: A factory for SQLAlchemy Session objects, which manage database conversations.
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Define the SQLAlchemy database URL.
# "sqlite:///./warehouse.db" specifies a persistent SQLite database file named 'warehouse.db' in the current directory.
SQLALCHEMY_DATABASE_URL = "sqlite:///./warehouse.db"

# Create the SQLAlchemy engine.
# This engine is responsible for database communication.
# connect_args={"check_same_thread": False} is required for SQLite when multiple threads might access the database,
# which is common in web applications like FastAPI.
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})

# Create a SessionLocal class.
# This class will be an instance of sessionmaker, configured for this specific engine.
# autocommit=False: Ensures that changes are not committed automatically.
# autoflush=False: Ensures that queries don't automatically flush pending changes to the database.
# bind=engine: Binds this sessionmaker to our created database engine.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create a declarative base class.
# This base class will be inherited by our ORM models (defined in models.py).
Base = declarative_base()

# Define a dependency function to get a database session.
# This function will be used by FastAPI's dependency injection system.
def get_db():
    # Create a new database session.
    db = SessionLocal()
    try:
        # Yield the session to the caller (FastAPI endpoint).
        # This makes the session available for database operations within the request.
        yield db
    finally:
        # Ensure the database session is closed after the request is finished,
        # even if an error occurs. This releases database resources.
        db.close()
