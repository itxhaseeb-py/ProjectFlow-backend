from sqlalchemy import create_engine 
from sqlalchemy.orm import sessionmaker
from app.core.config import settings


engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True    #checks that a pooled connection is still usable before SQLAlchemy hands it out.
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,  #prevents SQLAlchemy from automatically flushing pending changes before queries.
    autocommit=False  #makes transaction handling explicit.
)




