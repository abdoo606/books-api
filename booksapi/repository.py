"""In-memory repository behind a Protocol so the API never depends on storage details."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Protocol

from .models import Book, BookIn, BookPatch


@dataclass(slots=True)
class Filters:
    genre: str | None = None
    author: str | None = None
    min_rating: float | None = None
    max_price: int | None = None
    in_stock: bool | None = None
    q: str | None = None


class Repository(Protocol):
    def list(self, filters: Filters, *, limit: int, offset: int) -> tuple[list[Book], int]: ...
    def get(self, book_id: int) -> Book | None: ...
    def add(self, book: BookIn) -> Book: ...
    def update(self, book_id: int, patch: BookPatch) -> Book | None: ...
    def delete(self, book_id: int) -> bool: ...


@dataclass(slots=True)
class InMemoryRepo:
    _items: dict[int, Book] = field(default_factory=dict)
    _next_id: int = 1

    def add(self, book: BookIn) -> Book:
        created = Book(id=self._next_id, **book.model_dump())
        self._items[created.id] = created
        self._next_id += 1
        return created

    def get(self, book_id: int) -> Book | None:
        return self._items.get(book_id)

    def list(self, filters: Filters, *, limit: int, offset: int) -> tuple[list[Book], int]:
        matched = [b for b in self._items.values() if self._matches(b, filters)]
        matched.sort(key=lambda b: (-b.rating, b.title.lower()))
        return matched[offset : offset + limit], len(matched)

    @staticmethod
    def _matches(book: Book, f: Filters) -> bool:
        if f.genre and book.genre.lower() != f.genre.lower():
            return False
        if f.author and f.author.lower() not in book.author.lower():
            return False
        if f.min_rating is not None and book.rating < f.min_rating:
            return False
        if f.max_price is not None and book.price_cents > f.max_price:
            return False
        if f.in_stock is not None and book.in_stock is not f.in_stock:
            return False
        if f.q:
            needle = f.q.lower()
            haystack = f"{book.title} {book.author} {book.genre}".lower()
            if needle not in haystack:
                return False
        return True

    def update(self, book_id: int, patch: BookPatch) -> Book | None:
        book = self._items.get(book_id)
        if book is None:
            return None
        changes = {k: v for k, v in patch.model_dump().items() if v is not None}
        updated = book.model_copy(update=changes)
        self._items[book_id] = updated
        return updated

    def delete(self, book_id: int) -> bool:
        return self._items.pop(book_id, None) is not None
