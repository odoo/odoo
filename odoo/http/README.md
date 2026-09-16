# `odoo/http/` — the HTTP layer / WSGI application

This package prepares and dispatches every HTTP request to its controller: from
a raw request arriving on the WSGI entrypoint to a `Request` reaching a module
controller with a fully set-up ORM.

Application developers meet this package through `Controller` and the `@route`
decorator, which register the methods that deliver web content to matching URLs.

`doc/architecture/runtime.md` sketches this flow in three lines and
flattens it deliberately; **this file is the canonical, unflattened version.**
It lived in
`odoo/http/__init__.py`'s module docstring until `4ffeacacd8c` stripped
docstrings from `odoo/`, which left the sketch as the only surviving copy. It is
a document rather than a docstring now so that the strip policy and the call
graph stop competing for the same lines.

## Call graph

Every processing layer a request passes through before the `@route`-decorated
endpoint runs:

```
Application.__call__
    if path is like '/<module>/static/<path>':
        Request._serve_static

    elif not request.db:
        Request._serve_nodb
            App.nodb_routing_map.match
            Dispatcher.pre_dispatch
            Dispatcher.dispatch
                route_wrapper
                    endpoint
            Dispatcher.post_dispatch

    else:
        Request._serve_db
            env['ir.http']._match
            if not match:
                transaction.retrying(Request._serve_ir_http_fallback)
                    env['ir.http']._authenticate_explicit('public')
                    env['ir.http']._serve_fallback
                    env['ir.http']._post_dispatch
            else:
                transaction.retrying(Request._serve_ir_http)
                    env['ir.http']._authenticate
                    env['ir.http']._pre_dispatch
                    Dispatcher.pre_dispatch
                    Dispatcher.dispatch
                        env['ir.http']._dispatch
                            route_wrapper
                                endpoint
                    env['ir.http']._post_dispatch
```

The `Request._serve_*` methods are defined on `_RequestServeMixin` in
`_serve.py`; `Request` (in `request_class.py`) composes it.

## The stages

**`Application.__call__`** — WSGI entry point. Sanitizes the request, wraps it in
a werkzeug request and itself in an Odoo HTTP request, exposes it at
`http.request`, gives it an id (`request.id`: a well-formed `X-Request-Id` the
client sent, else a fresh token) that every log line of the request carries as
`rid:` and every response echoes as `X-Request-Id`, then forwards to `_serve_static`, `_serve_nodb` or `_serve_db`
depending on the request path and the presence of a database. Also responsible
for logging any error and encapsulating it in an HTTP error response.

**`Request._serve_static`** — streams an already-resolved file via
`Stream.prepare_response`. It does **not** resolve the path: `Application.get_static_file_path`
does, before the request reaches here, with `file_path()` plus a
`Path.resolve().is_relative_to()` containment check. There is one resolver on
purpose — a second one lived in this method until it was found to be unreachable.

**`Request._serve_nodb`** — handles `@route(auth='none')` endpoints when there is
no database connection. It matches the `auth='none'` endpoint from the request
path and delegates to the `Dispatcher`. An unmatched path infers a dispatcher
from the request's media type, exactly as `_serve_db` does, so a JSON client is
answered in JSON and a browser gets the `NOT_FOUND_NODB` page.

**`Request._serve_db`** — handles every non-static request when a database can be
reached. Opens a registry, manages the request cursor and environment, and
decides read-only versus read/write: `check_signaling`, `match` and
`serve_fallback` share one read-only cursor; `_serve_ir_http` reuses that same
(reset) read-only cursor, or a new read/write one.

**`Request._serve_aborted`** — handles explicit response control flow;
it does not appear in the graph above. An exception carrying
its own response (`abort(prepare_no_content_response())`, the CORS preflight) is delivered
verbatim; a status-less one goes through the dispatcher, so the error body
matches the route's media type rather than always being werkzeug's HTML page.
Inside a database transaction, `_serve_transaction_target` converts these
exceptions into returned responses so the transaction commits normally.

**`service.transaction.retrying`** — manages the cursor, the environment, and the
exceptions raised while executing the wrapped callable. Recovers from
serialization errors; resets the environment and **re-raises** everything else.
It does *not* attach an HTTP response — `_serve._update_served_exception`, which
wraps both `retrying()` calls, is what asks `ir.http._handle_error` for one. The
read-only → read/write promotion is `_serve_db`'s, not `retrying`'s: it catches
`psycopg.errors.ReadOnlySqlTransaction`, replays the retry participant and calls
`retrying()` a second time on a fresh read/write cursor. `retrying` also
performs the commit and signals registry changes once the callable returns.

**`ir.http._match`** — matches the controller endpoint corresponding to the
request path. Note the significant override for portal and website in the
`http_routing` module.

**`ir.http._serve_fallback`** — finds alternative ways to serve a request whose
path matches no controller: an attachment URL, a blog page, and so on. The
caller authenticates explicitly as `public`, including validation of an
authenticated cookie, before accessing these resources.

**`ir.http._authenticate`** — ensures the user on the current environment
satisfies `@route(auth=...)`. Using the ORM outside abstract models is unsafe
before this runs.

**`ir.http._pre_dispatch` / `Dispatcher.pre_dispatch`** — prepares the system for
the request; often saves extra query-string parameters in the session (`?debug=1`).

**`ir.http._dispatch` / `Dispatcher.dispatch`** — deserializes the request body
into `request.params` according to `@route(type=...)`, calls the endpoint, and
serializes the return value into a `Response`.

**`ir.http._post_dispatch` / `Dispatcher.post_dispatch`** — post-processes the
response: injects headers such as Content-Security-Policy and stages the
session through `Request._save_session()`. A database-bound request reserves a
rotation's new SID and token in memory, then persists the session and publishes
its cookie after a successful commit. Rollback restores the attempt's original
session. Error rendering starts after rollback, so an error handler can still
log out an expired session without preserving failed controller mutations.

Liveness is the request's call, not the page's: the store records the file's
mtime on load, and `_save_session` keeps a session alive — `utime` on the file
and a fresh cookie — once that age passes half the inactivity budget
(`sessions.max_inactivity_seconds` for an authenticated session,
`SESSION_LIFETIME` otherwise), whichever request notices first. An active
session therefore costs at most two liveness writes per budget window, and an
RPC-only client stays alive without ever loading a page.

`_save_session` decides: bound to the request's own live cursor it binds the
transaction and stages; otherwise it calls `_persist_session`, the one place
that writes the store and stages the cookie. `_bind_session_transaction`
registers cursor callbacks and captures the session snapshot. `_flush_session`
is idempotent: the postcommit callback invokes it, and the successful return
from `retrying` also invokes it for cursor adapters such as `TestCursor` that
suppress transaction callbacks; it persists through `_persist_session`.
`_restore_session_snapshot` is its rollback twin: the postrollback callback
invokes it, and so does `RequestRetryParticipant.on_rollback`; every call lands on
the same state, so the order does not matter. The snapshot stays armed until the
commit or the next bind, so a handler's own rollback followed by a retry still
restores. The one case that reads the disk: an explicit-environment save
(`request._save_session(env)` against another database) persisted the session
during the attempt, possibly rotating its file away — then the live copy under
the current sid is the identity the cookie must carry, and the snapshot's file
may no longer exist; `_load_session` reloads it without re-selecting the
database. A handler's own rollback clears the binding; a later save binds the
new transaction again.
Database-free requests and saves explicitly bound to another database keep
their immediate persistence path.
Read-only promotion is allowed only before commit, while the original cursor
is open. A postcommit SQL error propagates without replaying the handler.

The filesystem store serializes read/merge/write and revocation with stable
lock stripes shared by processes. A loaded session whose file has disappeared
cannot recreate that file. Saves merge changes against the loaded snapshot,
preserving independent top-level and nested dictionary edits; conflicting
edits to the same scalar or list still use the last writer. Rotation writes the
successor before changing the predecessor, and restores the original in-memory
identity if persistence fails. Filesystem persistence and PostgreSQL commit
remain separate: a filesystem failure after commit cannot undo database work.

Hard rotation revokes the whole session identifier family, including predecessor
cookies retained during soft rotation's grace period. A missing soft-rotation
successor is expired, never reconstructed. Soft rotation merges concurrent edits
before creating its successor; hard authentication transitions start a new family.
Login or logout upgrades an already staged soft rotation to a fresh hard family.
Late predecessor saves follow the live successor chain under the family lock;
adoption rejects a changed database or user rather than mixing authentication
state. A concurrent identity update merged before soft rotation gets a token
for the final user and successor SID. The in-memory integration store uses the
same merge and rotation logic, replacing only the storage operations.

**`ir.http._handle_error`** — absent from the graph; called for unmanaged
exceptions (serialization or read-only) raised inside
`service.transaction.retrying`. Returns an HTTP response wrapping the error.

**`Application._finalize_error_response`** — the error response built above
bypasses the normal dispatch flow, so the entrypoint runs
`Dispatcher.post_dispatch` over it explicitly before handing it to the WSGI
server. Without that step an error response would carry none of what
post-dispatch contributes — CORS headers, the `session_id` cookie and the session
save behind it, CSP — which is why the error path is the *only* place that calls
post_dispatch out of band. A request refused before its session was read (a
rejected method, a NUL in the path, a failing `_post_init`) has no session to
save and no dispatcher state to publish; it gets the security headers alone.

## Testing the pipeline without a database

`tests/_wsgi.py` runs `Application.__call__` end to end in the one-second tier: a
`Harness` owns a real `FilesystemSessionStore` on a temp directory, real routing
maps generated from controllers installed as a fake addon, and an in-memory
registry whose cursor commits and rolls back through the same `postcommit` /
`postrollback` callbacks the real one runs, with a fake `ir.http` that
authenticates, dispatches and renders errors the way `base`'s does. `Registry`,
`odoo.api.Environment` and the two database-list seams are patched for the call.
`tests/test_wsgi_pipeline.py` drives it: nodb and db routes, the committed
transaction, session publication after commit and rollback restore, login, the
negotiated 404, CSRF, JSON-RPC and json2, typed coercion, read-only promotion
with and without a replica, a controller bug, a rejected method, the header/
session database conflict. `test_http` on a real database remains the
integration gate; this is what runs before it. `tests/test_pipeline_costs.py` pins
the counts behind the two measured costs on the same harness: zero settings
derivations per request once the memo is warm, one store read per cookie and none
without one, one served-databases call per request, one cursor per database request
and none for a database-free one. Counts, not timings, so the guard holds on a
shared host.

## Module map

`doc/architecture/module.md` groups these modules into `[foundation]`,
`[serving]` and `[features]` tiers; the direction between them is the
`http-features-below-serving` contract, which holds `[foundation]` below
`[serving]` as well. `tests/test_layer_contract.py` checks it on every Tier-2
run (module-scope imports only; a `TYPE_CHECKING` block or a deferred import
does not count), and that no module of the package reaches `odoo.addons`.
`tests/test_observability_contract.py` holds the debug-logger discipline that the
retired checker held: every serving or feature module owns a `DebugLog`, and a broad
`except` that swallows must emit an event or a log line.

| Module | Tier | Contents |
|---|---|---|
| `__init__.py` | — | Public API: re-exports every symbol of the package |
| `application.py` | serving | `Application`: the WSGI callable, static/nodb/db routing decision, error logging and `_finalize_error_response` |
| `_serve.py` | serving | `_RequestServeMixin`: `_serve_static`, `_serve_nodb`, `_serve_db`, `_serve_aborted`, `_serve_ir_http`, `_serve_ir_http_fallback` |
| `request_class.py` | serving | `Request`, composed from the serve / response / CSRF / session mixins; what is left on the class itself is request identity (`params`, `cookies`, `best_lang`, `update_env`, the profiler hook, `_reset_for_replay`) |
| `_session_lifecycle.py` | serving | `_RequestSessionMixin`: loading the session and choosing the database (`_load_session`, `_select_dbname`), then staging, persisting, flushing and restoring it around the transaction (`_save_session`, `_persist_session`, `_bind_session_transaction`, `_flush_session`, `_restore_session_snapshot`) and folding the staged headers into the response |
| `_response.py` | serving | `_RequestResponseMixin`: `prepare_response`, `prepare_json_response`, redirects, `render` |
| `_csrf.py` | serving | `_RequestCsrfMixin`: CSRF token generation and validation |
| `dispatcher.py` | serving | `Dispatcher` and its three subclasses (`HttpDispatcher`, `JsonRPCDispatcher`, `Json2Dispatcher`), selected by `routing["type"]`. `pre_dispatch` also applies the request's statement budget: `@route(statement_timeout=<seconds>)`, or a dispatcher class's `statement_timeout`, is remembered by the request's cursor and armed as `SET LOCAL statement_timeout` before the first statement of every transaction it runs (a mid-request commit or the promotion replay keep it), so a runaway query on that route dies with the statement instead of the worker. A `json2` error body is an RFC 9457 problem document (`type`, `title`, `status`, `detail`, served as `application/problem+json`) followed by Odoo's own `name`, `message`, `arguments`, `context`, `debug` |
| `routing.py` | serving | `route()`, the `route_wrapper` it builds, `LazyCompiledBuilder` / `FasterRule`, `prepare_routing_map` (used by both maps the framework serves from), `_generate_routing_rules` over the assembled controllers, and the routing-parameter registry |
| `controller.py` | serving | `Controller`, the controller registry, and the assembly of one class per top controller from the installed modules' leaves (`_get_controllers`, `_group_controller_trees`) that the routing map is generated from |
| `session.py` | serving | `Session`: the mapping the request carries, its dirty/baseline tracking, login, logout and the hard-rotation demand |
| `_session_store.py` | serving | `SessionStore`, the policy every backend shares — keys, load, save with merge, soft and hard rotation, successor adoption, family revocation, keep-alive — over a seven-method storage surface (`_lock`, `_read`, `_write`, `_unlink`, `_touch`, `_sids_in_family`, `vacuum`). Three backends implement it: `FilesystemSessionStore` (stripe `flock`s shared across processes, atomic and optionally durable writes, sharded by the sid's first two characters), `PostgresSessionStore` (one `http_session` table in the database `http_session_db` names, `pg_advisory_xact_lock` per stripe, shared by every host) and `MemorySessionStore` (one `RLock`, this process only). `http_session_store` picks one; `Application.session_store` builds it |
| `stream.py` | serving | `Stream`: file/attachment streaming and conditional responses |
| `wrappers.py` | serving | `HTTPRequest`, `_Response`, `Headers`, `ResponseCacheControl`, `prepare_no_content_response`, `prepare_content_disposition_header`, `prepare_exception_response` — the werkzeug wrappers; the last is how the package turns an `HTTPException` into a facade `Response` (a status-less one answers 500), so werkzeug itself is no longer patched. **`HTTPRequest.environ` is a filtered copy**: every `werkzeug.*`, `wsgi.*` and `socket*` key is dropped except `wsgi.url_scheme` and `werkzeug.proxy_fix.orig`, so `environ["wsgi.input"]` raises `KeyError` — `raw_environ` is the unfiltered one |
| `_cookies.py` | serving | `FutureResponse` (the headers and cookies staged before a response exists), `get_cookie_identity`, the `set_cookie` defaults (consent, `Secure`, `SameSite`) and the same-identity de-duplication both `_Response` and `FutureResponse` set cookies through |
| `core.py` | serving | `_request_stack` (a werkzeug `LocalStack`), the `request` proxy bound to it, and `borrow_request` |
| `_dbfilter.py` | serving | `get_dbs_served` — the package's one database-listing entry point, cached — `filter_dbs_served` and the `dbfilter` machinery. The request never calls them directly: `Application.get_dbs_served(host)` / `filter_dbs_served(dbs, host)` are the injection point, which is what a test overrides |
| `_cors.py` | serving | `is_cors_preflight`, `resolve_cors_same_host`, and the header staging every dispatcher runs in `pre_dispatch`: `stage_cors_headers` (origin, credentials, methods, exposed headers) and `stage_preflight_headers` (max-age, allowed headers) |
| `_rpc.py` | serving | `dispatch_rpc` — the XML-RPC / JSON-RPC service dispatcher behind `/RPC2` and `/jsonrpc`, run with the request borrowed off the stack |
| `_error_serialization.py` | serving | `serialize_exception` and the dev-mode rule for what an error body may reveal |
| `_retry.py` | serving | `RequestRetryParticipant`: restores the session and rewinds uploads (`rewind_uploaded_files`) when `retrying()` replays a handler; passed explicitly by the request |
| `openapi.py` | features | `prepare_openapi_document`: an OpenAPI `3.1.0` document generated from the routing map — path and query parameters, JSON bodies with object schemas for dataclass and TypedDict parameters, `enum` / `minimum` / `maximum` / `pattern` from the constraints, `oneOf` with a `discriminator` for a discriminated union, and for `jsonrpc`/`json2` routes the response schema read from the handler's return annotation (`get_response_schema`), or `{}` — any JSON value — when there is none, inside the `{jsonrpc, id, result}` envelope for `jsonrpc` |
| `_params.py` | features | `ParamSpec` and the annotation-driven coercion behind `@route(typed=True)`: primitives, `list[...]`, `X | None`, `Literal[...]` and `Enum` choices, `Annotated[T, Range(ge=, le=)]` and `Annotated[str, Pattern(regex)]` constraints checked after coercion, and `@dataclass` or `TypedDict` types built field by field from a JSON object (unknown or missing required fields are a 400 naming the field; a class with an uncoercible field, or a recursive one, is left uncoerced; a constraint on an object or a list is declined). A union of object types is coerced when `Annotated[A | B, Discriminator("kind")]` names a field each member pins to one `Literal` value; the tag picks the variant and the variant validates the rest. An undiscriminated union stays uncoerced |
| `geoip.py` | features | `GeoIP` lookup exposed on the request (`_GeoIPNull` when unavailable) |
| `settings.py` | foundation | `HttpSettings`: the frozen snapshot of every option the serving tier reads (`dbfilter`, `db_name`, `dev_mode`, `x_sendfile`, `data_dir`, `server_wide_modules`, the GeoIP paths, `proxy_mode`/`proxy_hops`, `session_store`/`session_db` — validated: an unknown backend, or `postgres` without a database, refuses at the first read), `from_config` to build one, and the slot (`current`, `installed`, `override`) the package reads it through. The slot holds no snapshot in production: `current()` derives one from the live option dict, memoised on `config.generation` — a counter every write to any option layer moves, and one that answers a fresh object while a test has swapped `config.options` for a plain mapping — so a key written after boot still reaches the serving tier at the cost of one derivation, and a test that wants a fixed view installs its own |
| `constants.py` | foundation | Package-wide constants, `prepare_allow_header`, and the session and select-db path registries with their `is_select_db_path` predicate |
| `exceptions.py` | foundation | the HTTP exception vocabulary addon code raises — werkzeug's `NotFound`, `Forbidden`, `BadRequest`, `Unauthorized`, `HTTPException`, `abort` and the rest, re-exported so a controller never imports werkzeug — plus `RegistryError`, `SessionExpiredException`, `is_http_answer` (a 4xx is an answer, never a debugger case), and `get_error_response`/`set_error_response` — the only sanctioned way to read and write the `error_response` an exception carries |
| `_protocols.py` | foundation | `HttpExtension` — the `Protocol` `ir.http` satisfies, pinned by `TestIrHttpImplementsProtocol`; `Endpoint`/`HasRouting`/`RoutedMethod` for the attributes `@route` stuffs onto a handler. `RequestState` alone is `if TYPE_CHECKING:` — it is `object` at runtime |

## Related

- `doc/architecture/module.md` — the framework-wide subsystem map and the
  enforced dependency contracts, including `http-features-below-serving`.
- `doc/architecture/ARCHITECTURE.md` — the front door: context, forces,
  mechanisms, and the index of the views.
- `odoo/service/transaction.py` — `retrying()`, which owns commit and transaction
  retries. `_serve.py` owns read-only → read/write promotion.
