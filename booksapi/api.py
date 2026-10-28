from __future__ import annotations

from fastapi import Depends, FastAPI, Header, HTTPException, Query, status

from .models import Book, BookIn, BookPatch, Page, Token
from .repository import Filters, InMemoryRepo, Repository
from .security import Principal, issue_token, resolve


def create_app(repo: Repository | None = None) -> FastAPI:
    app = FastAPI(title="booksapi", version="1.0.0")
    app.state.repo = repo or InMemoryRepo()

    def current_user(authorization: str | None = Header(default=None)) -> Principal:
        if not authorization or not authorization.lower().startswith("bearer "):
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED, "missing bearer token", headers={"WWW-Authenticate": "Bearer"}
            )
        principal = resolve(authorization.split(" ", 1)[1].strip())
        if principal is None:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid token")
        return principal

    def admin_only(user: Principal = Depends(current_user)) -> Principal:
        if not user.is_admin:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "admin role required")
        return user

    @app.post("/auth/token", response_model=Token)
    def login(name: str = Query(min_length=1, max_length=50), role: str = Query(default="user", pattern="^(user|admin)$")) -> Token:
        """Demo login: a real service verifies a password hash here."""
        return Token(access_token=issue_token(name, role))

    @app.get("/books", response_model=Page)
    def list_books(
        genre: str | None = None,
        author: str | None = None,
        min_rating: float | None = Query(default=None, ge=0, le=5),
        max_price: int | None = Query(default=None, ge=0),
        in_stock: bool | None = None,
        q: str | None = Query(default=None, max_length=100),
        limit: int = Query(default=20, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
    ) -> Page:
        filters = Filters(genre, author, min_rating, max_price, in_stock, q)
        items, total = app.state.repo.list(filters, limit=limit, offset=offset)
        return Page(items=items, total=total, limit=limit, offset=offset)

    @app.get("/books/{book_id}", response_model=Book)
    def get_book(book_id: int) -> Book:
        book = app.state.repo.get(book_id)
        if book is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "book not found")
        return book

    @app.post("/books", response_model=Book, status_code=status.HTTP_201_CREATED)
    def create_book(book: BookIn, _: Principal = Depends(current_user)) -> Book:
        return app.state.repo.add(book)

    @app.patch("/books/{book_id}", response_model=Book)
    def patch_book(book_id: int, patch: BookPatch, _: Principal = Depends(current_user)) -> Book:
        if not patch.model_dump(exclude_none=True):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "no fields to update")
        updated = app.state.repo.update(book_id, patch)
        if updated is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "book not found")
        return updated

    @app.delete("/books/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_book(book_id: int, _: Principal = Depends(admin_only)) -> None:
        if not app.state.repo.delete(book_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "book not found")

    return app
