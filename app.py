# app.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List
import json
import os
from threading import Lock

app = FastAPI(title="Library Books API")

# --- Схемы (модели) ---
class BookIn(BaseModel):
    title: str = Field(..., min_length=1, description="Название книги")
    author: str = Field(..., min_length=1, description="Автор")
    year: int = Field(..., ge=0, description="Год издания (целое >= 0)")

class Book(BookIn):
    id: int

# --- Хранилище и синхронизация ---
DATA_FILE = "books.json"
books: List[Book] = []
_next_id = 1
lock = Lock()  # безопасный доступ при записи в файл

def load_books():
    """Загружает список книг из DATA_FILE, если файл есть."""
    global books, _next_id
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            books = [Book(**item) for item in data]
            if books:
                _next_id = max(b.id for b in books) + 1
            else:
                _next_id = 1

def save_books():
    """Сохраняет текущий список книг в DATA_FILE."""
    with lock:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump([b.dict() for b in books], f, ensure_ascii=False, indent=2)

@app.on_event("startup")
def on_startup():
    load_books()

# --- Endpoint-ы ---
@app.get("/books", response_model=List[Book])
def get_books():
    """Возвращает список всех книг."""
    return books

@app.get("/books/{book_id}", response_model=Book)
def get_book(book_id: int):
    """Возвращает книгу по id или 404."""
    for b in books:
        if b.id == book_id:
            return b
    raise HTTPException(status_code=404, detail="Book not found")

@app.post("/books", response_model=Book, status_code=201)
def create_book(payload: BookIn):
    """Создаёт новую книгу с автогенерацией id."""
    global _next_id
    new_book = Book(id=_next_id, **payload.dict())
    _next_id += 1
    books.append(new_book)
    save_books()
    return new_book

@app.put("/books/{book_id}", response_model=Book)
def update_book(book_id: int, payload: BookIn):
    """Обновляет существующую книгу по id или возвращает 404."""
    for i, b in enumerate(books):
        if b.id == book_id:
            updated = Book(id=book_id, **payload.dict())
            books[i] = updated
            save_books()
            return updated
    raise HTTPException(status_code=404, detail="Book not found")

@app.delete("/books/{book_id}", status_code=204)
def delete_book(book_id: int):
    """Удаляет книгу по id. Возвращает 204 No Content или 404."""
    for i, b in enumerate(books):
        if b.id == book_id:
            books.pop(i)
            save_books()
            return
    raise HTTPException(status_code=404, detail="Book not found")