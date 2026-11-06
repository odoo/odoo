# Batch ORM calls

Make **one** ORM call for the whole collection; an ORM call inside a
`for` loop over records or vals is a query per iteration. This covers
`search`, `search_count`, `_read_group` and `create` alike.

```python
# bad: one INSERT round-trip per record
for vals in vals_list:
    self.env['library.book'].create(vals)

# good: one batched create (and decorate overrides with @api.model_create_multi)
self.env['library.book'].create(vals_list)
```

```python
# bad: one aggregate query per author
for author in authors:
    author.book_count = Book.search_count([('author_id', '=', author.id)])

# good: one grouped query, then a dict lookup
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
  first) and the ORM prefetches each field for the whole set in one query;
  a record-by-record `browse(id)` loop defeats the prefetch.

## Exceptions

- A loop that only computes in memory on already-read fields is fine; the
  rule is about calls that hit the database.
- When a per-record call is truly unavoidable (e.g. an external API per
  record), bound the batch size.

# Search and read in one query

Use `search_fetch` instead of `search` when the records found are read right
after.

```python
# bad: one query for the ids, one for the fields
books = self.env['library.book'].search(domain)
titles = books.mapped('name')

# good: one query
books = self.env['library.book'].search_fetch(domain)
titles = books.mapped('name')
```

## Why

- `search` only returns ids: the first field read on them costs a second
  query, `search_fetch` gets the fields in the search query.

## Field list

- Leave the field list out: `search_fetch` then gets the fields marked
  `prefetch`, which is what the first read would get. A list misses the field
  the next change reads, and that read costs the second query again.
- Give the list when the model has large prefetched columns (long text, html)
  and every field read is known: it keeps them out of the query.

## Exceptions

- Records only written, unlinked or used for their ids need `search`.

# Do not read an x2many that grows without bound

Do not read an x2many that grows with the life of the record (messages,
followers, members, logs) to count it, test it or take a few records of it.
Ask the comodel: `search_count` to count, `search` or `search_fetch` with a
`limit` to take a few, `_read_group` for a count per record. The domain on
the comodel repeats the `domain` of the x2many field, and the `model` term
when the inverse is a `res_id` (`message_ids` of `mail.thread`).

```python
# bad: loads the id of every loan the book ever had
if len(book.loan_ids) > 25:
    ...
first_loan = book.loan_ids.sorted('id')[:1]

# good
Loan = self.env['library.loan']
if Loan.search_count([('book_id', '=', book.id)], limit=26) > 25:
    ...
first_loan = Loan.search([('book_id', '=', book.id)], order='id', limit=1)
```

## Why

- Reading the field selects the id of every related row and keeps it in
  cache, and a loop on the result then fetches every row. The cost follows
  the age of the record: it passes the tests and gets slow on an old
  database.

## Exceptions

- Code that needs every record of the x2many (copying a record with its
  lines) reads it whole.

# Performance conventions

- Put conditions in the search domain, not in `filtered()` on the result:
  `filtered` runs in Python on records already fetched. Reserve it for
  predicates a domain cannot express.
- **Reduce complexity.** Pre-map results into a dict (`{r['id']: r}`) instead of
  nested loops; cast membership-test collections to `set` (or use recordset
  arithmetic like `self - invalid`) to avoid O(n²).
- Index searched fields (`index=True`), selectively, per
  [Fields](fields.md#fields).
