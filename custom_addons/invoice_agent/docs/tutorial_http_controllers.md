# Odoo 19 internals: HTTP routing, requests, dispatchers, sessions and API keys

A ground-up tutorial for someone learning the Odoo framework, written while
reading the **actual** Odoo 19 sources in this repository. Every claim below
cites the file it comes from, so you can follow along:

| Concept | File in this repo |
|---|---|
| WSGI entry, request lifecycle, dispatchers, CSRF, sessions | `odoo/http.py` |
| Controller/routing map generation | `odoo/http.py` (`route`, `_generate_routing_rules`) |
| `auth` methods (`none`/`public`/`user`/`bearer`) | `odoo/addons/base/models/ir_http.py` |
| API keys (`res.users.apikeys`), password checks | `odoo/addons/base/models/res_users.py` |
| Portal controller patterns | `addons/portal/controllers/portal.py`, `addons/account/controllers/portal.py` |
| Real `csrf=False` justifications | `addons/web/controllers/database.py`, `addons/website/controllers/form.py` |
| HTTP test client | `odoo/tests/common.py` (`HttpCase`, `Opener`) |

The examples are the two endpoints implemented in
`custom_addons/invoice_agent/controllers/main.py`:

* `POST /invoice_agent/upload` — `type='http'`, `auth='none'` +
  bearer-token decorator, `csrf=False`
* `POST /invoice_agent/status/<int:move_id>` — `type='jsonrpc'`, `auth='user'`

---

## 1. The 50,000-foot call graph

`odoo/http.py` starts with a docstring that is worth reading twice. The flow
for a normal request is:

```
Application.__call__                       # WSGI entry point
  ├─ HTTPRequest(environ)                  # wraps raw WSGI env
  ├─ Request(httprequest)                  # Odoo request object
  │    └─ request._post_init()             # loads session, picks db
  ├─ request._serve_db()                   # db selected
  │    ├─ Registry(db), RO cursor          # build registry, check signaling
  │    ├─ ir.http._match(path)             # match controller route → rule,args
  │    ├─ Request._set_request_dispatcher  # pick HttpDispatcher or JsonRPCDispatcher
  │    ├─ switch to RW cursor if needed
  │    └─ service.model.retrying(serve)    # run with retries
  │         └─ ir.http._authenticate(rule.endpoint)   # auth='none|public|user|bearer'
  │              └─ ir.http._pre_dispatch             # per-route size limit, lang
  │                   └─ dispatcher.dispatch          # deserialize params
  │                        └─ ir.http._dispatch       # call ORM controller method
  │                             └─ route_wrapper      # filter args, Response.load
  │                   └─ ir.http._post_dispatch       # save session, CSP headers
  └─ exception → request.dispatcher.handle_error(exc) # maps to HTTP status
```

Read the three dispatch entry points carefully — they are the skeleton of the
whole layer:

1. `Request._serve_static` serves `/module/static/...` straight off disk.
2. `Request._serve_nodb` runs `auth='none'` "server-wide" routes when no
   database is selected (login, database manager).
3. `Request._serve_db` is the big one — it opens a registry, matches the
   controller, and dispatches. **Key subtlety**: it first tries a
   **read-only cursor**; a route marked `readonly=True` runs on that RO cursor.
   If a "readonly" route attempts a write, the framework catches
   `psycopg2.errors.ReadOnlySqlTransaction` and retries on a read/write cursor
   (that is why a wrongly-marked route still works, just slower). A normal
   read/write route starts a fresh RW transaction.

---

## 2. `@route(...)` — the decorator and the merged routing

`route(route=None, **routing)` in `odoo/http.py`:

```python
def route(route=None, **routing):
    ...
    def decorator(endpoint):
        ...
        if routing.get('type') == 'json':
            warnings.warn(
                "Since 19.0, @route(type='json') is a deprecated alias to @route(type='jsonrpc')",
                DeprecationWarning, ...)
            routing['type'] = 'jsonrpc'
        assert routing.get('type', 'http') in _dispatchers.keys(), ...
        ...
```

**Odoo 19 rename spelled out**: `type='json'` now just warns and is remapped
to `type='jsonrpc'`. Prefer `'jsonrpc'` directly. The accepted values are the
keys of the `_dispatchers` dict — `'http'`, `'jsonrpc'`, and `'json2'` — each
with its own dispatcher class (see §4).

The decorator also wraps the endpoint in `route_wrapper`, which:

* filters out parameters the endpoint does not accept (with a warning);
* for `type='http'` routes, converts the return value with
  `Response.load(result)` (see §5).

The `auth` values, from the same docstring:

| `auth` | Meaning | Request uid |
|---|---|---|
| `'user'` | must be logged in (session) | the session user |
| `'bearer'` | `Authorization: Bearer <apikey>`, else falls back to session | apikey user / session user |
| `'public'` | logged in or `base.public_user` | user or public user |
| `'none'` | always active, even with no db | `None` (no ORM access) |

Routing inheritance: `_generate_routing_rules` walks the MRO of every subclass
of `Controller`, merges the `original_routing` dicts going ancestor → leaf
(leaf wins per key), and only emits routes for installed modules. That is why
a re-decorated override can omit arguments — the previous ones are kept.

---

## 3. The `Request` object and `request.env`

`request` is a *thread-local* (`werkzeug.local.LocalStack` + the module-level
`request = _request_stack()`). Inside a controller, `from odoo.http import
request` gives you the request for *this* HTTP worker thread.

`Request` exposes, among many others:

* `request.httprequest` — the underlying `werkzeug.wrappers.Request`:
  `files`, `form`, `args`, `headers`, `method`, `remote_addr`,
  `content_length`, `environ`.
* `request.env` — the ORM environment bound to the current request's cursor,
  user and context. **This is how a controller reaches models**:
  `request.env['account.move'].create(...)`.
* `request.env.uid`, `request.env.user`, `request.env.cr` — uid / user
  recordset / database cursor. (In Odoo 19 the old `request.uid`,
  `request.cr`, `request.context` shortcuts are deprecated, they warn and
  forward to `request.env.*`.)
* `request.session` — the current session dict-like (see §7).
* `request.params` — set by the dispatcher right before the controller runs.
* `request.update_env(user=..., context=..., su=...)` — **rebind** the
  environment. This is the exact mechanism used by the bearer decorator in
  our upload endpoint, and by `ir.http._auth_method_bearer` internally.
* `request.make_response(data, headers, cookies, status)` and
  `request.make_json_response(data, ...)` — build raw / JSON responses
  (see §5).
* `request.render(template, qcontext)` — lazy QWeb rendering, returns a
  `Response` that is flattened at dispatch time
  (`ir.http._dispatch`: `if result.is_qweb: result.flatten()`).
* `request.csrf_token(...)` / `request.validate_csrf(...)` — see §8.

When is `request.env` *bound*? Only inside `_serve_db`, after a registry is
open. Note `_auth_method_none` rebinds it with **uid `None`**:

```python
@classmethod
def _auth_method_none(cls):
    request.env = api.Environment(request.env.cr, None, request.env.context)
    request.env.transaction.default_env = request.env
```

`Request.update_env` keeps the same cursor and swaps the user:

```python
def update_env(self, user=None, context=None, su=None):
    cr = None  # None keeps the same cursor
    self.env = self.env(cr, user, context, su)
    self.env.transaction.default_env = self.env
    threading.current_thread().uid = self.env.uid
```

**Why the upload endpoint uses `auth='none'` + a decorator**: with
`auth='user'`, an anonymous caller never reaches your code — `ir.http`
raises `SessionExpiredException` first and `HttpDispatcher.handle_error`
answers with a **redirect to `/web/login`** (an HTML page). A machine route
must answer **JSON 401** instead, so we disable the session pre-filter with
`auth='none'`, and authenticate inside the endpoint with the
`_require_bearer_auth` decorator (§6). If you switch the route to
`auth='user'` or `auth='public'` you can observe the deliberate failures in
§10.

---

## 4. Dispatchers: `http` vs `jsonrpc` (was `json`)

`Dispatcher` is an abstract base; each concrete dispatcher registers itself
in `_dispatchers[routing_type]`. The request is matched to a dispatcher in
`Request._set_request_dispatcher` using the route's `type`.

### HttpDispatcher — `routing_type='http'`

Compatible with any request (`is_compatible_with` returns `True`).

```python
def dispatch(self, endpoint, args):
    self.request.params = dict(self.request.get_http_params(), **args)
    # CSRF check for unsafe methods when route wants it (default True)
    if self.request.httprequest.method not in SAFE_HTTP_METHODS \
       and endpoint.routing.get('csrf', True):
        token = self.request.params.pop('csrf_token', None)
        if not self.request.validate_csrf(token):
            raise werkzeug.exceptions.BadRequest('Session expired (invalid CSRF token)')
    if self.request.db:
        return self.request.registry['ir.http']._dispatch(endpoint)
    return endpoint(**self.request.params)
```

* **Params sources**: `request.get_http_params()` merges query-string
  (`args`) + urlencoded form + multipart `files`. So a `-F file=@bill.pdf`
  curl upload lands in `request.httprequest.files['file']`.
* **CSRF default is ON** for `type='http'` (see §8).

### JsonRPCDispatcher — `routing_type='jsonrpc'`

Compatible only when the client sends `Content-Type: application/json`
(or `application/json-rpc`):

```python
@classmethod
def is_compatible_with(cls, request):
    return request.httprequest.mimetype in cls.mimetypes
```

`dispatch()`:

1. reads the raw body with `request.get_json_data()`
   (i.e. `json.loads(request.httprequest.get_data(as_text=True))`);
2. builds `request.params = dict(jsonrequest.get('params', {}), **args)` —
   **the route's `<int:move_id>` path argument is merged into params**;
3. calls the endpoint and serializes the return value into a full
   JSON-RPC 2.0 envelope:

   ```python
   {'jsonrpc': '2.0', 'id': <echoed id>, 'result': <endpoint return>}
   ```

So a `jsonrpc` controller returns a plain dict; the envelope is added for you.
Our status endpoint therefore returns:

```python
{
    "move_id": move.id,
    "ai_extraction_status": move.ai_extraction_status,
    "ai_confidence": move.ai_confidence,
    ...
}
```

Client request shape (this is what `curl` must send):

```json
{"jsonrpc": "2.0", "method": "call", "id": 1,
 "params": {}}
```

plus `Content-Type: application/json`.

**Note on "/invoice_agent/status/<int:move_id>"**: JSON-RPC over GET does not
make sense and `methods=['POST']` is the right call — the Odoo web client
always POSTs JSON-RPC. With `auth='user'`, an anonymous `curl` gets a
JSON-RPC *error envelope* (HTTP 200, code `100`, "Odoo Session Expired")
rather than a redirect — because `JsonRPCDispatcher.handle_error`
special-cases `SessionExpiredException` to code 100. That is why
`type='jsonrpc'` keeps `auth='user'` while the `type='http'` upload route
needs `auth='none'`.

There is also a third dispatcher, `Json2Dispatcher` (`type='json2'`) — a
JSON body that is *not* wrapped in the JSON-RPC envelope. It is used by some
internal endpoints; you will not need it for this exercise.

### Error mapping (status codes)

`HttpDispatcher.handle_error`:

| Exception | Result |
|---|---|
| `SessionExpiredException` | redirect to `/web/login?redirect=...` |
| `HTTPException` (incl. our `BadRequest`, `Unauthorized`, `NotFound`) | the exception itself (its `code`/`get_response`) |
| `UserError` (and subclasses) | `HTTPStatus` mapped from `exc.http_status` (422 default) |
| anything else | `InternalServerError()` → 500 |

`JsonRPCDispatcher.handle_error` packs everything into a JSON-RPC `error`
object with `code` (404 for `NotFound`, 100 for `SessionExpired`, else 0).

That is how a leaked traceback becomes a clean response: **raise a
`werkzeug.exceptions.HTTPException` subclass** instead of letting a raw
`Exception` bubble out. In the upload controller we raise `BadRequest(...)`
for bad input and `Unauthorized(response=json_body)` for auth failures. When
you exercise the endpoints with curl (§11) and hit an unexpected traceback,
convert it into a `BadRequest` with a clean message — that is the workflow
this exercise is built around.

---

## 5. Responses: `Response.load`, `make_response`, `make_json_response`

For `type='http'`, `route_wrapper` ends with
`return Response.load(result)`. `Response.load` accepts:

* a `Response` — used as-is;
* a `werkzeug.wrappers.Response` — converted;
* **an `HTTPException` — it is re-raised** (so returning an exception and
  raising it behave the same);
* `str` / `bytes` / `None` — wrapped in `Response(result)`.

Practical helpers used by the codebase:

* `request.make_json_response(data, headers=None, cookies=None, status=200)`
  — JSON-serializes `data`, sets `Content-Type: application/json`.
  The upload endpoint uses `status=201` (Created).
* `request.make_response(data, headers=[('Name', 'value'), ...], status=200)`
  — arbitrary bytes/str payload with custom headers. The portal
  controllers use this to stream PDFs:
  `addons/account/controllers/portal.py`:
  `return request.make_response(docs_data[0]['content'], list(headers.items()))`.
* `request.render(template, qcontext)` — lazy QWeb; the `portal.py`
  home page does `return request.render("portal.portal_my_home", values)`.

A JSON response body inherits `Content-Type: application/json; charset=utf-8`
automatically; `make_json_response` also sets `Content-Length`.

---

## 6. Tracing real controllers: portal and account patterns

Read these three files next — they are the canonical examples of the
patterns in the previous sections.

### `addons/portal/controllers/portal.py`

* **Routing converters**. `@route(['/my/invoices', '/my/invoices/page/<int:page>'], type='http', auth='user', website=True)` and `@route(['/my/invoices/<int:invoice_id>'], type='http', auth='public', website=True)`. The `<int:...>` converters are implemented by
  `SignedIntConverter` in `odoo/addons/base/models/ir_http.py`
  (`_get_converters`), a `NumberConverter` subclass. `_match` runs
  `routing_map.bind_to_environ(...).match(path_info=..., return_rule=True)`,
  so the path segment is captured and passed as the method argument.
* **`_document_check_access(model_name, document_id, access_token)`**. The
  portal's protected-document pattern:
  * browse the record, switch to `SUPERUSER_ID` with `.with_user(SUPERUSER_ID)`,
  * `.exists()` → `MissingError` if gone,
  * `document.check_access('read')` → `AccessError` if the current user
    cannot read it,
  * fallback: if an `access_token` is supplied and matches the record's
    `access_token` (compared with `consteq` to avoid timing attacks), access
    **is** granted — that is how emailed portal links work.
  Both errors are caught by the caller and turned into `request.redirect('/my')`.
* **`request.render` for QWeb pages** — `portal_my_invoice_detail` builds a
  values dict, then `request.render("account.portal_invoice_page", values)`.
* **`request.make_response` with custom headers** — `_show_report`:
  `headers = self._get_http_headers(...)`; returns
  `request.make_response(report, headers=list(headers.items()))`, where the
  headers include `Content-Type: application/pdf` and
  `Content-Disposition` (via `content_disposition`).

### `addons/account/controllers/portal.py`

* `PortalAccount(CustomerPortal)` — controller inheritance: subclass the
  portal `CustomerPortal`, re-route `/my/invoices` etc.
* Concrete invoice detail: `portal_my_invoice_detail(self, invoice_id,
  access_token=None, report_type=None, download=False, **kw)` immediately does
  `self._document_check_access('account.move', invoice_id, access_token)` in
  a try/except that redirects to `/my` on `(AccessError, MissingError)`. This
  is the exact pattern a token-protected document route follows.
* `methods=['GET','POST']` and per-method branches:
  `request.httprequest.method == 'POST'` — a real-world example of
  dual-use routes (`portal_my_journal_unsubscribe`).

### Every `csrf=False` in the core addons — and why

A search of the whole tree found:

```
addons/web/controllers/database.py:
  /web/database/create       auth="none"  methods=['POST']  csrf=False
  /web/database/duplicate    auth="none"  methods=['POST']  csrf=False
  /web/database/drop         auth="none"  methods=['POST']  csrf=False
  /web/database/backup       auth="none"  methods=['POST']  csrf=False
  /web/database/restore      auth="none"  methods=['POST']  csrf=False, max_content_length=None
  /web/database/change_password auth="none" methods=['POST'] csrf=False
addons/website/controllers/form.py:
  /website/form/<string:model_name>  auth="public"  methods=['POST']  website=True  csrf=False, captcha='website_form'
```

`addons/account/controllers/portal.py` and
`addons/portal/controllers/portal.py` contain **no** `csrf=False`: the portal
forms keep the default (CSRF on) and embed the token in QWeb forms. The
pattern that justifies `csrf=False`:

1. **Machine / cross-origin callers that never carry a session cookie** —
   the `/web/database/*` manager routes run before login, in `auth="none"`,
   called by the database-manager page via sub-resource or by tools. There is
   no session to protect, and the CSRF token (which is derived from the
   session id, §8) is meaningless.
2. **A bearer-token- or captcha-authenticated machine route** —
   `/website/form/...` pairs `csrf=False` with `captcha='website_form'`: the
   captcha replaces CSRF as the anti-abuse control. In our module the upload
   route pairs `csrf=False` with the bearer-API-key decorator: the key in the
   `Authorization` header is *not* automatically attached by browsers, so the
   classic CSRF vector (browser auto-sends cookies) does not apply.

Rule of thumb: **keep `csrf=True` (default) for browser form posts; use
`csrf=False` only on token- or captcha-authenticated machine routes, and
justify it in a comment.** Exactly what `InvoiceAgentController.invoice_agent_upload`
does.

---

## 7. Sessions: `res.users.apikeys`, session tokens, CSRF tokens

### The session

`Session` (in `odoo/http.py`) is a `MutableMapping` persisted to
`session_store` (a `FilesystemSessionStore` in `session_dir`, default
`~/.local/share/Odoo/sessions` or config). Default keys — `get_default_session()`:

```python
{
    'context': {},
    'create_time': time.time(),
    'db': None,
    'debug': '',
    'login': None,
    'uid': None,
    'session_token': None,
    '_trace': [],
}
```

`Request._get_session_and_dbname` picks the session from the `session_id`
cookie (validating the sid format), then picks the db from the session / the
`X-Odoo-Database` header / the single configured db.

The session token: on login, `res.users.finalize` stores
`session_token = env.user._compute_session_token(self.sid)`, an HMAC-SHA256
of the sid keyed by a tuple of user fields + the `database.secret`
(`_get_session_token_fields`: id, login, password, active).
`ir.http._authenticate_explicit` calls `security.check_session(...)` against
that token to prove the session wasn't tampered with, and `Session.logout`
kills it. `FilesystemSessionStore.rotate` (hard/soft) regenerates the sid —
that is why password changes log you out everywhere.

### `_check_credentials` and the `res.users.apikeys` table

`ResUsers._check_credentials(credential, env)` in
`odoo/addons/base/models/res_users.py`:

* with a `type: 'password'` credential: verify against
  `CryptContext().verify_and_update`, optionally re-encrypting hashes that
  became weaker (the `pbkdf2_sha512` + old `plaintext` placeholder);
* non-interactive (`interactive: False` — i.e. XML-RPC or anything that is not
  the web login): if the password hash fails, it *also* tries
  `res.users.apikeys._check_credentials(scope='rpc', key=password)`.

The `res.users.apikeys` model (`_auto = False`, a hand-rolled table):

```sql
CREATE TABLE res_users_apikeys (
    id serial primary key,
    name varchar not null,
    user_id integer not null REFERENCES res_users(id) ON DELETE CASCADE,
    scope varchar,
    expiration_date timestamp without time zone,
    index varchar(8) not null CHECK (char_length(index) = 8),
    key varchar not null,
    create_date timestamp without time zone DEFAULT (now() at time zone 'utc')
)
```

Generation (`_generate`): 20 random bytes → hex (`API_KEY_SIZE`), stored
**hashed** with passlib `pbkdf2_sha512` (6000 rounds), and the **first 8 hex
digits** are stored as a plaintext `index` for fast lookup. So the plaintext
key is shown once and never stored — exactly why the UI shows it only in the
"API Key Ready" wizard.

Validation (`_check_apikey_credentials(cr, scope, key, table)`) — the exact
SQL our bearer decorator triggers via
`request.env['res.users.apikeys']._check_credentials(scope='rpc', key=token)`:

```python
SELECT user_id, key
FROM res_users_apikeys INNER JOIN res_users u ON (u.id = user_id)
WHERE u.active and index = %(index)s
  AND (scope IS NULL OR scope = %(scope)s)
  AND (expiration_date IS NULL OR expiration_date >= now() at time zone 'utc')
```

then `KEY_CRYPT_CONTEXT.verify(key, stored_hash)` and returns the `user_id`.

Important scope semantics (from the `_check_credentials` docstring in
`res_users.py`): **`'rpc'` is not a real scope** — a key with `scope IS NULL`
(global key, created from the UI "Developer API Keys") matches *any* requested
scope, while a scoped key must match exactly. So:

| key created with | `scope='rpc'` check | remark |
|---|---|---|
| UI "Developer API Key" | `scope` is NULL → matches | the recommended key for our upload |
| `_generate('rpc', ...)` | exact match | programmatic |
| `_generate('website', ...)` | no match (`'rpc' != 'website'`, scope not NULL) | → 401 |

That is how a "wrong scope" key is rejected: `_check_apikey_credentials`
returns `None`, and the decorator raises JSON 401.

### `ir.http._auth_method_bearer` — Odoo 19 native bearer auth

```python
@classmethod
def _auth_method_bearer(cls):
    ...
    if token := get_http_authorization_bearer_token():
        uid = request.env['res.users.apikeys']._check_credentials(scope='rpc', key=token)
        if not uid:
            raise Unauthorized(e, www_authenticate=WWWAuthenticate('bearer'))
        ...
        request.update_env(user=uid)
        request.session.can_save = False  # stateless
    elif not request.env.uid:
        raise Unauthorized(e, www_authenticate=WWWAuthenticate('bearer'))
    ...
```

Two lessons for our machinery:

1. The *exact* resolution calls are `_check_credentials(scope='rpc', key=token)`
   then `request.update_env(user=uid)` — our `_require_bearer_auth` decorator
   is a hand-rolled copy of this.
2. Setting `request.session.can_save = False` makes the request **stateless** —
   no session cookie round-trip. The `@route(..., save_session=False)`
   argument does the same thing declaratively; we use it on the upload route.

---

## 8. CSRF in depth: the token derivation and validation

CSRF protects *browser-session* requests against cross-site forgery. Odoo's
implementation (in `Request.csrf_token` / `Request.validate_csrf`):

```python
secret   = env['ir.config_parameter'].sudo().get_param('database.secret')
max_ts   = int(time.time() + (time_limit or CSRF_TOKEN_SALT))  # 1y
msg      = f'{session.sid[:STORED_SESSION_BYTES]}{max_ts}'.encode()  # 42+chars
hm       = hmac.new(secret.encode('ascii'), msg, hashlib.sha1).hexdigest()
token    = f'{hm}o{max_ts}'
```

So the token is an HMAC-SHA1 of `(first 42 chars of the session id, expiry)`
keyed by the server secret `database.secret`. `validate_csrf` recomputes it
and compares with `const_eq` (constant-time), also rejecting expired tokens.

`HttpDispatcher.dispatch` enforces it:

* only for methods **not** in `SAFE_HTTP_METHODS = ('GET','HEAD','OPTIONS','TRACE')`
* only if `endpoint.routing.get('csrf', True)` — default True for `http`;
  *`jsonrpc` routes default to no CSRF* because the request body is JSON and
  the Content-Type check (`is_compatible_with`) already rejects browser form
  posts.
* the token is looked up in `request.params.pop('csrf_token', None)` — i.e.
  sent as a form field named `csrf_token`.

QWeb forms embed it via
`<input type="hidden" name="csrf_token" t-att-value="request.csrf_token()"/>` —
this is precisely why the account/portal forms keep `csrf=True`.

---

## 9. The invoice_agent endpoints — annotated tour

Everything above is exercised in
`custom_addons/invoice_agent/controllers/main.py`. Line-by-line:

```python
MAX_UPLOAD_BYTES = 10 * 1024 * 1024          # 10 MiB guard
ALLOWED_MIMETYPES = ("application/pdf",)
```

**Upload route**:

```python
@http.route("/invoice_agent/upload",
            type="http", auth="none", methods=["POST"],
            csrf=False, save_session=False)
@_require_bearer_auth                            # our decorator
def invoice_agent_upload(self, **kwargs):
```

* `type="http"` → `HttpDispatcher` parses the multipart body.
* `auth="none"` → no session pre-filter; the decorator is the only gate
  (JSON 401 instead of HTML redirect).
* `methods=["POST"]` → only POST allowed; other verbs get `405 Method Not
  Allowed` (`FasterRule`/werkzeug routing).
* `csrf=False` → justified above: bearer-authenticated machine route.
* `save_session=False` → stateless: no session cookie is ever emitted.

Body handling mirrors `HttpDispatcher` itself: `request.httprequest.files`
is a `werkzeug.datastructures.FileStorage`; `.read()` gives raw bytes, `.filename`
and `.content_type` the metadata. We validate **before** touching
`ir.attachment`:

```python
if len(raw) > MAX_UPLOAD_BYTES:
    raise BadRequest(_("File too large: ..."))
if content_type not in ALLOWED_MIMETYPES:
    raise BadRequest(_("Unsupported file type ..."))
```

Then `ir.attachment.create({'name': ..., 'raw': raw, 'mimetype': ...})` —
`raw` is a `fields.Binary` holding the exact bytes (`datas` would force
base64; we verified `raw = fields.Binary` exists in
`odoo/addons/base/models/ir_attachment.py`). We set `res_model`/`res_id` so
the file becomes attached to the upcoming `account.move`.

Then the move is created **already inside the extraction state machine**:

```python
move = request.env["account.move"].create({
    "move_type": "in_invoice",
    "ai_source_attachment_id": attachment.id,
    "ai_extraction_status": "pending",
    "ai_confidence": 0.0,
})
move._invoice_agent_schedule_extraction()   # placeholder → "processing"
```

`account.move.journal_id` is `required=True` but `compute='_compute_journal_id'`
with `precompute=True` — creating a vendor bill auto-fills the default
purchase journal, which is why only `move_type`, the attachment and the AI
fields are needed. (`ai_extraction_status` defaults to `"pending"` on the
field definition; we re-state it for clarity.)

Finally `request.make_json_response({...}, status=201)` returns the id.

**Status route**:

```python
@http.route("/invoice_agent/status/<int:move_id>",
            type="jsonrpc", auth="user", methods=["POST"])
def invoice_agent_status(self, move_id, **kwargs):
    move = request.env["account.move"].browse(move_id)
    if not move.exists():
        raise NotFound(f"account.move {move_id} does not exist")
    return {
        "move_id": move.id,
        "ai_extraction_status": move.ai_extraction_status,
        "ai_confidence": move.ai_confidence,
        "ai_review_required": move.ai_review_required,
    }
```

The `<int:move_id>` converter passes `move_id` as a plain int; the
`JsonRPCDispatcher` merges the JSON body `params` with the path arg, wraps the
returned dict into the JSON-RPC envelope. A client polling with
`{"jsonrpc":"2.0","method":"call","id":1,"params":{}}` sees the state.

---

## 10. Compare auth modes with deliberate failures

Best done with `curl` (you must first log in to get a session cookie — see
§11). The same route body, three different `auth` values:

| route `auth` | anonymous `curl -X POST /invoice_agent/upload` | What you see |
|---|---|---|
| `'user'` | `SessionExpiredException` raised in `ir.http._authenticate` | `302` → `Location: /web/login?redirect=%2Finvoice_agent%2Fupload` (HTML) |
| `'public'` | binds `base.public_user`; the *endpoint* then rejects (our decorator: no `Authorization` → JSON 401) | `401` with JSON body `{"error": ...}` |
| `'none'` | decorator gate only | `401` JSON (missing/invalid key), works with valid key |

How to observe:

```bash
# no session, auth='none' route: decorator answers JSON 401
curl -s -i -X POST https://invoices.example.com/invoice_agent/upload

# auth='user' variant of the same route (temporarily change auth="user"):
curl -s -i -c session.txt -X POST https://invoices.example.com/invoice_agent/upload
# -> 302 Found, Location: /web/login?...

# then log in and retry with the session cookie:
curl -s -i -c session.txt -b session.txt \
  -F "login=admin" -F "password=..." https://invoices.example.com/web/login
curl -s -i -b session.txt -X POST https://invoices.example.com/invoice_agent/upload
```

Note the *login* route (`/web/login`, `auth="none"`) may be protected by
`ensure_db()` in a multi-db setup; add `?db=<database>` per the Odoo docs.

---

## 11. Exercising the real endpoints with curl over HTTPS

Your deployment terminates TLS at nginx (see `nginx/conf.d/odoo.conf` and
`docs/deployment.md`), so use `https://invoices.<domain>/...`. The bearer key
comes from **My Profile → Account Security → Developer API Keys** (a global
key, `scope NULL` — matches our `scope='rpc'` check).

### Upload a real scanned bill (multipart)

```bash
curl -sS \
  -H "Authorization: Bearer <your-report-api-key>" \
  -F "file=@bill.pdf;type=application/pdf" \
  https://invoices.<domain>/invoice_agent/upload
```

Expected (201):

```json
{"jsonrpc": "2.0", "id": null,
 "result": {"move_id": 42, "name": "VEND/2026/08/0001",
            "state": "draft", "ai_extraction_status": "processing"}}
```

Negative cases to exercise:

```bash
# no token
curl -s -o /dev/null -w '%{http_code}\n' \
  -F file=@bill.pdf https://invoices.<domain>/invoice_agent/upload          # 401
# garbage token
curl -s -H "Authorization: Bearer abc" -F file=@bill.pdf \
  https://invoices.<domain>/invoice_agent/upload                             # 401
# wrong mimetype
curl -s -H "Authorization: Bearer <key>" -F "file=@bill.txt;type=text/plain" \
  https://invoices.<domain>/invoice_agent/upload                             # 400
# oversized (create an 11 MiB file)
dd if=/dev/zero of=huge.pdf bs=1M count=11
curl -s -H "Authorization: Bearer <key>" -F "file=@huge.pdf;type=application/pdf" \
  https://invoices.<domain>/invoice_agent/upload                             # 400
```

### Poll the JSON-RPC status endpoint

```bash
curl -sS -b session.txt -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"call","id":1,"params":{}}' \
  https://invoices.<domain>/invoice_agent/status/42
# -> {"jsonrpc":"2.0","id":1,"result":{"move_id":42,
#     "ai_extraction_status":"processing","ai_confidence":0.0,
#     "ai_review_required":false}}
```

While you poll, the cron `AI: Retry Stuck Extractions` (from
`data/automation_data.xml`) will reset moves stuck in `processing` for more
than an hour back to `pending`.

### Inspect the stored key hash

```sql
-- connected to the Odoo database (docker exec ... psql -U odoo)
SELECT index, left(key, 20) || '...' AS key_prefix, scope, expiration_date
FROM res_users_apikeys;
```

The `index` column shows the first 8 hex chars (plaintext, for fast lookup);
`key` holds the `pbkdf2_sha512$...` hash. The plaintext key itself is never
stored — that is why the UI shows it exactly once.

---

## 12. Recommended workflow: py_compile, upgrade, route test, tests

```bash
# 1. syntax-check the new package
python -m py_compile custom_addons/invoice_agent/controllers/__init__.py \
                     custom_addons/invoice_agent/controllers/main.py \
                     custom_addons/invoice_agent/tests/test_controllers.py \
                     custom_addons/invoice_agent/models/account_move.py

# 2. install/upgrade the module so routes are registered
docker compose exec odoo odoo-bin -u invoice_agent -d <database> --stop-after-init

# 3. confirm the route appears in the routing map
docker compose exec odoo odoo-bin shell -d <database> --no-http
# >>> from odoo.http import root
# (easier: hit the URL and read the error, or grep the logs after a curl)

# 4. run the test suite for this module (HttpCase is post_install)
docker compose exec odoo odoo-bin -d <database> --test-tags /invoice_agent \
  --stop-after-init --disable-cron -i invoice_agent
```

The HttpCase tests in `tests/test_controllers.py` cover exactly the negative
cases from this section (401 missing / invalid / wrong-scope token,
400 oversized / non-PDF / missing file, plus the 201 happy path and the
jsonrpc session-expired envelope), so fixing the real curl failures and
fixing the tests is the same work.

---

## 13. Checklist of what you have learned

- [ ] The Odoo 19 request lifecycle: WSGI entry → `Request._serve_db` →
  route match → `_authenticate` → dispatcher.dispatch → controller → error
  handling.
- [ ] `type='http'` vs `type='jsonrpc'` (and the deprecated `'json'` alias).
- [ ] `auth='user' / 'public' / 'none' / 'bearer'` and their request `uid`s;
  why machine routes use `auth='none'` + an explicit auth decorator.
- [ ] How `request.env` is bound and rebound (`request.update_env`).
- [ ] How werkzeug HTTP exceptions map to status codes per dispatcher
  (`SessionExpiredException` → `/web/login` redirect for http, code 100 for
  jsonrpc; `HTTPException` passes through; unknown → 500).
- [ ] Portal routing converters, `_document_check_access`,
  `request.make_response` with headers, `request.render` for QWeb.
- [ ] Session storage, session token (HMAC), CSRF token derivation
  (HMAC of `sid_head + expiry` under `database.secret`), and the
  browser vs machine-route justification for `csrf=False`.
- [ ] `res.users.apikeys`: hashed `key`, plaintext `index`, scope (`NULL` =
  global), expiration, and the exact `_check_apikey_credentials` SQL.
- [ ] `HttpCase.url_open` (which auto-wraps in `allow_requests`) and how to
  write negative HTTP tests.

The definitive next-stop docs: the `@route` reference at
https://www.odoo.com/documentation/19.0/developer/reference/backend/http.html
and the testing reference at
https://www.odoo.com/documentation/19.0/developer/reference/backend/testing.html.
