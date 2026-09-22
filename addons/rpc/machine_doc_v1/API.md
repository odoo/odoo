# rpc — the doors a program calls

Two doors reach every model of an Odoo database, and one health route beside
them. `openapi.json` in this directory is their contract as this commit
serves it: the document `prepare_openapi_document` renders from `rpc`'s own
routes, checked in so a client generator has a fixed file to read rather
than a running server to ask.

| Door | Route | Auth | Note |
|---|---|---|---|
| JSON | `POST /json/2/<model>/<method>` | `bearer` | the door; the body is the method's keyword arguments |
| JSON (refusal) | `/json/2`, `/json/2/<subpath>` | `public` | answers "Did you mean POST /json/2/<model>/<method>?" |
| XML-RPC | `/xmlrpc/2/<service>` | `none` | deprecated; warns once per client |
| XML-RPC (legacy) | `/xmlrpc/<service>` | `none` | the pre-2 path, same services |
| Version | `/json/version`, `/web/version` | `none` | the server's version, for a client's handshake |

`/jsonrpc` is gone (odoo `3e11e95be4d2`): a client that posted
`{"service": …, "method": …, "args": …}` there speaks to a door that no
longer exists.

## The document

- **It is `rpc`'s doors alone**, not the server's. `/web/openapi.json`
  renders whatever the database has installed and is a different document on
  every database; this one moves only when `rpc` does, which is what makes it
  worth checking in.
- **It is OpenAPI 3.1**, whose schema objects are JSON Schema 2020-12;
  `TestOpenAPIContract` validates every one of them with the validator's own
  meta-schema, so the check needs no network.
- **Regenerate it** when a door changes:

  ```bash
  ODOO_WRITE_OPENAPI=1 odoo-bin -d <db> --test-enable \
      --test-tags /rpc:TestOpenAPIContract.test_the_checked_in_document_is_current
  ```

  Without the variable the same test fails and says so: the checked-in
  contract and the served one cannot drift apart in silence.

## What the document states, and what it cannot

A route says what it takes only where its handler declares it: `typed=True`
and an annotation per parameter (E8533 `route-untyped` holds every machine
route to that). `POST /json/2/<model>/<method>` takes the model and the
method in its path and the method's own keyword arguments in its body, so
its `requestBody` is an open object — the arguments of `search_read` are
not a fact of the route but of the model's method, and `/doc` (api_doc)
answers that per model.

`security` is the route's `auth`: `bearer` renders `bearerAuth` (an HTTP
bearer token, a `res.users.apikeys` key), `user` a session cookie, and
`public`/`none` an empty requirement — an open door, stated as one.
