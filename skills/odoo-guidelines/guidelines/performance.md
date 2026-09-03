# Batch ORM calls

Make **one** ORM call for the whole collection; an ORM call inside a
`for` loop over records or vals is a query per iteration. This covers
`search`, `search_count`, `_read_group` and `create` alike.

```python
# bad — one INSERT round-trip per record
for vals in vals_list:
    self.env['library.book'].create(vals)

# good — one batched create (and decorate overrides with @api.model_create_multi)
self.env['library.book'].create(vals_list)
```

```python
# bad — one aggregate query per author
for author in authors:
    author.book_count = Book.search_count([('author_id', '=', author.id)])

# good — one grouped query, then a dict lookup
counts = {
    author.id: count
    for author, count in Book._read_group(
        [('author_id', 'in', authors.ids)], ['author_id'], ['__count'],
    )
}
for author in authors:
    author.book_count = counts.get(author.id, 0)
```

## Why

- Each call is a full round-trip (Python → SQL → Python); a loop turns O(1)
  queries into O(n) and dominates response time on real data volumes.
- Reading fields batches too: iterate a recordset (or `browse` all ids
  first) and the ORM prefetches each field for the whole set in one query —
  a record-by-record `browse(id)` loop defeats the prefetch.

## Exceptions

- A loop that only computes in memory on already-read fields is fine — the
  rule is about calls that hit the database.
- When a per-record call is truly unavoidable (e.g. an external API per
  record), bound the batch size.

# Performance conventions

- Put conditions in the search domain, not in `filtered()` on the result:
  `filtered` runs in Python on records already fetched. Reserve it for
  predicates a domain cannot express.
- **Reduce complexity.** Pre-map results into a dict (`{r['id']: r}`) instead of
  nested loops; cast membership-test collections to `set` (or use recordset
  arithmetic like `self - invalid`) to avoid O(n²).
- Index searched fields (`index=True`) — selectively, per
  [Fields](fields.md#fields).
