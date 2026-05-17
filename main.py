import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
import uvicorn
from dotenv import load_dotenv


from database import Database
from data import indexer

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    db_path = os.getenv("DB_PATH")
    db = Database(db_path)
    db.create_tables()
    db.clear()
    indexer(db)
    app.state.db = db

    yield

    db.close()

app = FastAPI(lifespan=lifespan)


@app.get("/")
async def read_root():
    return {"status": "ready", "message": "completed"}

@app.get("/api/files")
async def get_files():
    db = app.state.db
    files = db.get_files()
    return files

@app.get("/api/files/{name}/structure")
async def get_files(name: str):
    db = app.state.db
    return db.get_file_structure(name)


@app.get("/api/search")
async def search(q: str, type: str = None):
    db = app.state.db
    results = db.search_files(q, type_filter=type)

    return {
        "query": q,
        "filter_applied": type,
        "query_results": results
    }

@app.get("/api/stats")
async def get_stats():
    db = app.state.db
    return db.get_stats()

if __name__ == "__main__":
    host = os.getenv("HOST")
    port = int(os.getenv("PORT"))
    uvicorn.run("main:app", host=host, port=port, reload=True)