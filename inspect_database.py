from src.database.connection import get_connection

with get_connection() as connection:
    tables = connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()

    for table in tables:
        name = table["name"]

        columns = connection.execute(
            f"PRAGMA table_info({name})"
        ).fetchall()

        print(f"\n{name}:")
        print(", ".join(column["name"] for column in columns))