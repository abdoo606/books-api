# 12 · booksapi

A complete REST API: auth, filtering, pagination, PATCH semantics.

## Run

```bash
uvicorn booksapi.api:create_app --factory
```

## Test

```bash
pytest projects/12-books-api -q
```

## What it demonstrates

- Repository behind a `Protocol`, so storage can be swapped without touching routes
- Bearer auth with constant-time token comparison; admin-only destructive routes
- Validation lives in Pydantic models, not in hand-written `if` chains
- Correct status codes: 401 vs 403 vs 404 vs 409 vs 422
