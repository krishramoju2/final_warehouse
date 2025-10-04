This file sets up SQLAlchemy for use in apps like FastAPI by:

creating a database engine (connection manager),

preparing a SessionLocal factory for request-scoped sessions,

defining a Base class for ORM models,

and exposing a get_db() dependency that gives each request its own DB session and ensures it closes after use.


create_engine → builds the connection engine.

connect_args={"check_same_thread": False} is only for SQLite to allow multi-threaded access.

declarative_base → creates a base class (Base) that all ORM models inherit from.

sessionmaker → factory to generate Session objects:

autocommit=False → must call db.commit() manually.

autoflush=False → no automatic flush before queries.

bind=engine → sessions tied to the engine.

Database URL → "sqlite:///./inmemory.db" creates a file inmemory.db in current directory (not true in-memory; that’s sqlite:///:memory:).

Base = declarative_base() → needed for defining ORM models and creating tables with Base.metadata.create_all(bind=engine).

get_db() → FastAPI dependency that:

yields a fresh session per request,

closes it after use (prevents connection leaks).

Can be extended to rollback on errors.
