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

# Use search_fetch when the domain and the rules are simple

`search_fetch` reads the fields in the search query and saves a query.
Use it when the domain and the record rules of the model are simple. With
joins or heavy rules, keep `search`: the fields in the same query can lead
PostgreSQL to a worse plan, and the second query, on the primary key, is
cheap. Fewer queries is not always faster.

```python
# two queries: one for the ids, one for the fields
books = self.env['library.book'].search(domain)
titles = books.mapped('name')

# one query, only the fields read
books = self.env['library.book'].search_fetch(domain, ['name'])
titles = books.mapped('name')
```

## Why

- `search` only returns ids: the first field read on them costs a second
  query, `search_fetch` gets the fields in the search query.

## Field list

- Give the list when the fields read are known, more so when some are not
  prefetched by default or when many records are expected: it keeps the
  other columns out of the query and out of memory.
- Leave it out when the fields read are not known: `search_fetch` then gets
  the fields marked `prefetch`, as the first read would. A list that misses
  a field read later costs the second query again.

## Exceptions

- Records only unlinked or used for their ids need `search`.

# Do not read an x2many that grows without bound

Do not read an x2many that can reach thousands of rows over the life of
the record (messages, followers, members, logs) to count it, test it or
take a few records of it.
Ask the comodel: `search_count` to count, `search` or `search_fetch` with a
`limit` to take a few, `_read_group` for a count per record. The domain on
the comodel repeats the `domain` of the x2many field, and the term on the
model field of the inverse (`res_model`) when the inverse is a `res_id`.
When the field has `bypass_search_access=True`, reading it skips the
access checks of the comodel: run the query with `sudo()` to get the same
records, and bring them back with `.sudo(False)` before reading their
fields.

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

- An x2many that stays small (tags, lines of a payment term) is read directly:
  one read is cheaper than a query on the comodel.
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
