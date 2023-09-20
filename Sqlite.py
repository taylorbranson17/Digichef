import sqlite3


class DatabaseError(Exception):
    pass
class IntegrityError(Exception):
    pass

class SqliteDriver:

    def __init__(self, filename: str)-> None:
        self.filename = filename

    def __enter__(self):
        try:
            self.conn = sqlite3.connect(self.filename, isolation_level=None)
            self.conn.row_factory = sqlite3.Row
            self.cursor = self.conn.cursor()
            return self.cursor
        except sqlite3.IntegrityError as err:
            raise IntegrityError(err)
    
    def __exit__(self, exc_type, exc_value, exc_tb):
        self.conn.close()
        if exc_type is sqlite3.OperationalError:
            raise DatabaseError(exc_value)
        elif exc_type:
            raise exc_type(exc_value)