DB_CONFIG = {
    "dbname": "edison",
    "user": "edison",
    "password": "edison_password",
    "host": "localhost",
    "port": 5432
}

LOCAL_DB = f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']}"