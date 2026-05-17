import ast
import os
import logging
from database import Database


def indexer(db: Database) -> None:
    directory = os.getenv("DATASET_PATH")
    if not os.path.exists(directory):
        logging.error(f"Ошибка: директория {directory} не найдена!")
        return

    files = sorted([f for f in os.listdir(directory) if f.endswith('.py') and f != '__init__.py'])

    for file in files:
        file_data = {
            "name": file,
            "doc": '',
            "funcs": [],
            "classes": []
        }
        file_path = os.path.join(directory, file)
        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                code = f.read()
                tree = ast.parse(code)
                file_data['doc'] = ast.get_docstring(tree) or ""
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef) and node.name != "__init__":
                        file_data['funcs'].append({
                            "name": node.name,
                            "doc": ast.get_docstring(node) or "",
                            "start": node.lineno,
                            "end": node.end_lineno,
                        })
                    elif isinstance(node, ast.ClassDef):
                        file_data['classes'].append({
                            "name": node.name,
                            "doc": ast.get_docstring(node) or "",
                            "start": node.lineno,
                            "end": node.end_lineno,
                        })

                db.add_file(file_data)
            except SyntaxError:
                logging.error(f"Ошибка в файле: {file}")