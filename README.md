This file sets up SQLAlchemy for use in apps like FastAPI by:

creating a database engine (connection manager),

preparing a SessionLocal factory for request-scoped sessions,

defining a Base class for ORM models,

and exposing a get_db() dependency that gives each request its own DB session and ensures it closes after use.


