from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from booksapi.api import create_app
from booksapi.models import BookIn, BookPatch
from booksapi.repository import Filters, InMemoryRepo
from booksapi import security

BOOKS = [
    {"title": "Clean Code", "author": "Robert Martin", "genre": "programming", "year": 2008, "price_cents": 3500, "rating": 4.5},
    {"title": "The Pragmatic Programmer", "author": "Andrew Hunt", "genre": "programming", "year": 1999, "price_cents": 4200, "rating": 4.8},
    {"title": "Dune", "author": "Frank Herbert", "genre": "scifi", "year": 1965, "price_cents": 1200, "rating": 4.9},
]


@pytest.fixture()
def client():
    security.reset()
    repo = InMemoryRepo()
    for book in BOOKS:
        repo.add(BookIn(**book))
    with TestClient(create_app(repo)) as c:
        yield c


def auth(client, role="user") -> dict[str, str]:
    token = client.post(f"/auth/token?name=tester&role={role}").json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------- models
def test_whitespace_is_collapsed():
    book = BookIn(title="  Clean   Code ", author=" Robert ", year=2008, price_cents=100)
    assert book.title == "Clean Code"


def test_blank_title_rejected():
    with pytest.raises(ValidationError):
        BookIn(title="   ", author="x", year=2008, price_cents=1)


def test_year_bounds():
    with pytest.raises(ValidationError):
        BookIn(title="x", author="y", year=1200, price_cents=1)


def test_patch_is_all_optional():
    assert BookPatch().model_dump(exclude_none=True) == {}


# ------------------------------------------------------------ repository
def test_filters_combine():
    repo = InMemoryRepo()
    for book in BOOKS:
        repo.add(BookIn(**book))
    items, total = repo.list(Filters(genre="programming", min_rating=4.6), limit=10, offset=0)
    assert total == 1 and items[0].title == "The Pragmatic Programmer"


def test_search_is_case_insensitive_across_fields():
    repo = InMemoryRepo()
    for book in BOOKS:
        repo.add(BookIn(**book))
    items, total = repo.list(Filters(q="frank"), limit=10, offset=0)
    assert total == 1


def test_sorting_is_rating_then_title():
    repo = InMemoryRepo()
    for book in BOOKS:
        repo.add(BookIn(**book))
    items, _ = repo.list(Filters(), limit=10, offset=0)
    assert [b.rating for b in items] == sorted([b.rating for b in items], reverse=True)


def test_pagination_slices_without_losing_total():
    repo = InMemoryRepo()
    for book in BOOKS:
        repo.add(BookIn(**book))
    items, total = repo.list(Filters(), limit=2, offset=2)
    assert total == 3 and len(items) == 1


# --------------------------------------------------------------- the api
def test_list_and_filter(client):
    assert client.get("/books").json()["total"] == 3
    assert client.get("/books?genre=scifi").json()["items"][0]["title"] == "Dune"


def test_limit_validation(client):
    assert client.get("/books?limit=500").status_code == 422
    assert client.get("/books?offset=-1").status_code == 422


def test_get_missing_book(client):
    assert client.get("/books/999").status_code == 404


def test_write_requires_token(client):
    payload = {"title": "New", "author": "A", "year": 2020, "price_cents": 100}
    assert client.post("/books", json=payload).status_code == 401
    assert client.post("/books", json=payload, headers={"Authorization": "Bearer nope"}).status_code == 401


def test_create_book(client):
    payload = {"title": "New Book", "author": "Someone", "year": 2021, "price_cents": 990, "rating": 3.75}
    response = client.post("/books", json=payload, headers=auth(client))
    assert response.status_code == 201
    body = response.json()
    assert body["id"] == 4 and body["rating"] == 3.8


def test_patch_updates_only_given_fields(client):
    response = client.patch("/books/1", json={"price_cents": 100}, headers=auth(client))
    assert response.status_code == 200
    assert response.json()["price_cents"] == 100
    assert response.json()["title"] == "Clean Code"


def test_empty_patch_is_rejected(client):
    assert client.patch("/books/1", json={}, headers=auth(client)).status_code == 422


def test_delete_requires_admin(client):
    assert client.delete("/books/1", headers=auth(client)).status_code == 403
    assert client.delete("/books/1", headers=auth(client, role="admin")).status_code == 204
    assert client.get("/books/1").status_code == 404


def test_invalid_login_role(client):
    assert client.post("/auth/token?name=x&role=root").status_code == 422


def test_tokens_are_unique(client):
    assert auth(client)["Authorization"] != auth(client)["Authorization"]
