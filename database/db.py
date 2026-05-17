import sqlite3
import logging

logging.basicConfig(level=logging.INFO)


class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.connection = sqlite3.connect(db_path)
        self.connection.execute("PRAGMA foreign_keys = ON;")
        self.connection.create_function("LOWER_UTF8", 1, lambda x: x.lower() if x else x)
        self.cursor = self.connection.cursor()

    def create_tables(self) -> None:
        query = """
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            docstring TEXT
        );

        CREATE TABLE IF NOT EXISTS functions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            docstring TEXT,
            start INTEGER NOT NULL,
            end INTEGER NOT NULL,
            FOREIGN KEY (file_id) REFERENCES files (id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS classes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            docstring TEXT,
            start INTEGER NOT NULL,
            end INTEGER NOT NULL,
            FOREIGN KEY (file_id) REFERENCES files (id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_functions_name ON functions(name);
        CREATE INDEX IF NOT EXISTS idx_functions_doc ON functions(docstring);
        CREATE INDEX IF NOT EXISTS idx_classes_name ON classes(name);
        CREATE INDEX IF NOT EXISTS idx_classes_doc ON classes(docstring);
        """

        try:
            self.cursor.executescript(query)
            self.connection.commit()
            logging.info("База данных была успешно проинициализирована")
        except sqlite3.Error as e:
            self.connection.rollback()
            logging.error(f"Ошибка при создании таблиц: {e}")

    def clear(self) -> None:
        self.cursor.execute("DELETE FROM files;")
        self.cursor.execute("DELETE FROM sqlite_sequence WHERE name='files';")
        self.cursor.execute("DELETE FROM sqlite_sequence WHERE name='functions';")
        self.cursor.execute("DELETE FROM sqlite_sequence WHERE name='classes';")
        self.connection.commit()
        logging.info("База данных была успешно очищена")

    def add_file(self, file: dict) -> None:
        try:
            query = """INSERT INTO files (name, docstring) VALUES (?, ?)"""
            self.cursor.execute(query, (file["name"], file["doc"]))
            file_id = self.cursor.lastrowid

            func_query = """INSERT INTO functions (file_id, name, docstring, start, end)
            VALUES (?, ?, ?, ?, ?)"""
            data_func = [
                (file_id, f['name'], f['doc'], f['start'], f['end'])
                for f in file['funcs']
            ]
            self.cursor.executemany(func_query, data_func)

            class_query = """INSERT INTO classes (file_id, name, docstring, start, end)
                        VALUES (?, ?, ?, ?, ?)"""
            data_class = [
                (file_id, c['name'], c['doc'], c['start'], c['end'])
                for c in file['classes']
            ]
            self.cursor.executemany(class_query, data_class)

            self.connection.commit()
            logging.info(f"Файл {file['name']} успешно проиндексирован")
        except sqlite3.Error as e:
            self.connection.rollback()
            logging.error(f"Ошибка add_file: {e}")

    def get_files(self) -> list[dict]:
        try:
            query = """
            SELECT
                f.id,
                f.name,
                COUNT(func.id) as functions_count
            FROM files f
            LEFT JOIN functions func ON f.id = func.file_id
            GROUP BY f.id
            """
            self.cursor.execute(query)
            rows = self.cursor.fetchall()
            result = []
            for row in rows:
                result.append({
                    "id": row[0],
                    "name": row[1],
                    "functions_count": row[2]
                })
            return result
        except sqlite3.Error as e:
            logging.error(f"Ошибка get_files: {e}")
            return []

    def get_file_structure(self, file_name: str) -> dict:
        try:
            self.cursor.execute("SELECT id, name, docstring FROM files WHERE name = ?", (file_name,))
            file_row = self.cursor.fetchone()

            if not file_row:
                return []

            file_id = file_row[0]

            self.cursor.execute(
                "SELECT name, docstring, start, end FROM functions WHERE file_id = ?",
                (file_id,)
            )
            funcs = [
                {"name": r[0], "docstring": r[1], "start": r[2], "end": r[3]}
                for r in self.cursor.fetchall()
            ]

            self.cursor.execute(
                "SELECT name, docstring, start, end FROM classes WHERE file_id = ?",
                (file_id,)
            )
            classes = [
                {"name": r[0], "docstring": r[1], "start": r[2], "end": r[3]}
                for r in self.cursor.fetchall()
            ]

            return {
                "id": file_id,
                "name": file_row[1],
                "docstring": file_row[2],
                "functions": funcs,
                "classes": classes
            }
        except sqlite3.Error as e:
            logging.error(f"Ошибка get_file_structure: {e}")
            return []

    def search_files(self, keyword: str, type_filter: str = None) -> list[dict]:
        try:
            search_pattern = f"%{keyword.lower()}%"

            func_part = """
            SELECT 'function' as type, name, docstring, start, end 
            FROM functions 
            WHERE LOWER_UTF8(name) LIKE ? OR LOWER_UTF8(docstring) LIKE ?
            """

            class_part = """
            SELECT 'class' as type, name, docstring, start, end 
            FROM classes 
            WHERE LOWER_UTF8(name) LIKE ? OR LOWER_UTF8(docstring) LIKE ?
            """

            if type_filter == "function":
                query = func_part
                params = (search_pattern, search_pattern)
            elif type_filter == "class":
                query = class_part
                params = (search_pattern, search_pattern)
            elif not type_filter:
                query = f"{func_part} UNION ALL {class_part}"
                params = (search_pattern, search_pattern, search_pattern, search_pattern)

            self.cursor.execute(query, params)
            rows = self.cursor.fetchall()

            return [
                {
                    "type": r[0],
                    "name": r[1],
                    "docstring": r[2],
                    "start": r[3],
                    "end": r[4]
                }
                for r in rows
            ]
        except sqlite3.Error as e:
            logging.error(f"Ошибка search_files: {e}")
            return []

    def get_stats(self):
        try:
            query = """
            SELECT 
                (SELECT COUNT(*) FROM files) as total_files,
                (SELECT COUNT(*) FROM functions) as total_functions,
                (SELECT COUNT(*) FROM classes) as total_classes
            """
            self.cursor.execute(query)
            row = self.cursor.fetchone()

            return {
                "total_files": row[0],
                "total_functions": row[1],
                "total_classes": row[2]
            }
        except sqlite3.Error as e:
            logging.error(f"Ошибка в get_stats: {e}")
            return []

    def close(self) -> None:
        self.connection.close()