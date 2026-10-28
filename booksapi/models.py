"""Domain + validation. Pydantic models double as the API contract."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class BookIn(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    author: str = Field(..., min_length=1, max_length=120)
    genre: str = Field(default="general", max_length=40)
    year: int = Field(..., ge=1400, le=2100)
    price_cents: int = Field(..., ge=0, le=10_000_00)
    rating: float = Field(default=0.0, ge=0, le=5)
    in_stock: bool = True

    @field_validator("title", "author", "genre")
    @classmethod
    def strip_and_collapse(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if not cleaned:
            raise ValueError("must not be blank")
        return cleaned

    @field_validator("rating")
    @classmethod
    def round_rating(cls, value: float) -> float:
        return round(value, 1)


class Book(BookIn):
    id: int


class BookPatch(BaseModel):
    title: str | None = None
    author: str | None = None
    genre: str | None = None
    year: int | None = None
    price_cents: int | None = None
    rating: float | None = None
    in_stock: bool | None = None


class Page(BaseModel):
    items: list[Book]
    total: int
    limit: int
    offset: int


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
