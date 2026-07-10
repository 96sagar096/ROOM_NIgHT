import urllib.parse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import get_settings

settings = get_settings()

db_url = settings.database_url
connect_args = {}

# Normalize connection strings for PostgreSQL and MySQL drivers
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+psycopg://", 1)
elif db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)
elif db_url.startswith("mysql://"):
    db_url = db_url.replace("mysql://", "mysql+pymysql://", 1)

# Handle SSL parameters for PyMySQL
if db_url.startswith("mysql+pymysql://") or db_url.startswith("mysql://"):
    parsed = urllib.parse.urlparse(db_url)
    query_params = urllib.parse.parse_qs(parsed.query)
    
    has_ssl = False
    ssl_keys_to_remove = ["ssl-mode", "ssl_mode", "sslmode"]
    for key in ssl_keys_to_remove:
        if key in query_params:
            has_ssl = True
            break
            
    if has_ssl:
        # Rebuild URL without the ssl-mode parameters so PyMySQL doesn't crash
        clean_params = {k: v for k, v in query_params.items() if k not in ssl_keys_to_remove}
        new_query = urllib.parse.urlencode(clean_params, doseq=True)
        parsed = parsed._replace(query=new_query)
        db_url = urllib.parse.urlunparse(parsed)
        connect_args["ssl"] = {}

if db_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(db_url, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
