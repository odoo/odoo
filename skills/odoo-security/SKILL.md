---
name: odoo-security
description: >-
  Security audit of Odoo addon code: access control (ir.access, field groups,
  sudo), injection (SQL, domain, eval, XSS via Markup/markup()), untrusted
  public methods/RPC,
  controller auth/CSRF, file access, deserialization, returning complex
  objects, getattr/setattr, timing attacks. Use when auditing an addon, or
  judging whether a specific construct (a sudo, raw SQL, a route, …) is safe.
---

# Security audit of Odoo code

Audit Odoo addons for the framework-specific ways access control and injection
go wrong. When a feature needs more access than the rules give, it gets the
minimum, in the narrowest scope, with a comment saying why; a silent widening
(a bare `sudo()`, a loosened access row) is a finding.

## Process

- Review the `security/` data files against [Access control](#access-control).
- Sweep the addon for every pattern in the table below; judge each hit against
  its section. A hit is not a finding by itself — the sections say what makes
  it one.
- Report each finding with severity, exact file/line, and a minimal fix.

The audit is complete when every pattern has been swept and every hit judged.

| Sweep for | Judge against |
| --- | --- |
| `sudo(`, `with_user(`, `with_company(` | [Don't over-sudo](#dont-over-sudo) |
| `cr.execute`, `SQL(`, `.format`/`%`/f-string near SQL | [Use the ORM; parameterize SQL](#use-the-orm-parameterize-sql) |
| domain built from request, RPC, or stored field values | [Domain injection](#domain-injection) |
| public (non-`_`) model methods | [Default to private methods](#default-to-private-methods) |
| `@http.route(`, bare `@route(` | [Routes: auth, POST, CSRF](#routes-auth-post-csrf) |
| `innerHTML`, `insertAdjacentHTML`, `markup(` (JS), `Markup(` (Python), `t-raw` (dead code) | [Prevent XSS](#prevent-xss-escape-on-the-way-into-the-dom) |
| password/token/secret fields | [Field-level access](#field-level-access) |
| `related=` crossing models (sudo-computed by default) | [Field-level access](#field-level-access) |
| `open(` | [Open files with `file_open`](#open-files-with-file_open-not-open) |
| `eval(`, `exec(`, `safe_eval` | [`eval` is evil](#eval-is-evil) |
| `pickle` | [Never `pickle`](#never-pickle) |
| `getattr(`, `setattr(` on records | [`getattr`/`setattr`](#getattrsetattr-are-not-your-friends) |
| `==` comparing a secret/token | [Timing attacks](#timing-attacks) |
| `def f(..., x=[])` / `x={}` | [Mutable default arguments](#mutable-default-arguments) |
| methods returning rich objects | [Don't return complex objects](#dont-return-complex-objects-from-model-methods) |

## Access control

Mechanics of `ir.access` rows and field `groups` are in the `odoo-guidelines`
skill ([Access rights](../odoo-guidelines/guidelines/security.md#access-rights),
[Fields](../odoo-guidelines/guidelines/fields.md#fields)); audit `security/` with
the attacker's reading:

- Flag any `c`/`u`/`d` operation granted to `base.group_everyone`,
  `base.group_portal`, or `base.group_public`; scrutinize even `r` on models
  holding personal or business-sensitive data.
- A permission row's `operation` set is what it grants; a *restriction*
  (group-less) row covering only some operations leaves the others governed by
  the permission rows alone — if any permission grants `write`, an attacker
  can alter records the read restriction hides (`write` checks write access
  only, never read). Cover **all** CRUD operations that need restricting.
- Multi-company models need a company restriction row; sensitive models need
  domain restrictions, not just group permissions.

## Field-level access

- A field's `groups` attribute removes it from views and `fields_get` and
  raises on explicit read/write. Use it for sensitive fields instead of
  relying on the UI to hide them.
- **Passwords and API tokens**: restrict them with `groups="base.group_system"`,
  or `groups=fields.NO_ACCESS` to hide the field from everyone, admins
  included. A token field on a model with a permissive access row is readable
  by any user via `search_read`.
- **`related` fields are sudo-computed by default** (`related_sudo=True`): a
  related field reaching sensitive data through a user-writable `Many2one`
  lets the user point the M2o at an arbitrary record and read the related
  value with elevated rights — set `related_sudo=False` on sensitive chains.
  (`readonly=False` write-through is a separate concern: it runs in the
  user's environment and is access-checked.)

## Default to private methods

- **Any public method is callable via RPC** with attacker-chosen arguments;
  the records in `self` and the parameters **cannot be trusted** (access
  control is only enforced on CRUD, not method calls). More public methods =
  bigger attack surface. **Prefix methods with `_` by default**; drop the `_`
  only when the method is genuinely meant to be called externally — and then
  validate inputs. (Privacy alone isn't a control: a `_`-method fed untrusted
  data is still dangerous.)
- The RPC guard (`get_public_method`) blocks `_`-prefixed names,
  classmethods/staticmethods, and anything decorated `@api.private` anywhere
  in the MRO — check that before flagging a public-named method as exposed;
  `@api.private` is the sanctioned fix when renaming would break callers.

## Use the ORM; parameterize SQL

- Never use the cursor directly when the ORM can do it: raw SQL bypasses
  access control, translations, field invalidation, and `active` handling.
  Prefer `search`/`_read_group` and direct field access (not `read()`). For
  custom SQL over ORM-filtered rows, build the query with `_search(...)` and
  `Query.select(SQL(...))`: access rules and `active` handling stay in force.
- When you must write SQL, **never** interpolate with `+`/`%`/`.format`. Pass
  values as **parameters** (psycopg2 formats them, including a tuple for
  `IN %s`), or use the `odoo.tools.SQL` wrapper. For dynamic **identifiers**
  (table/column names, which can't be parameters) use `SQL.identifier(name)`,
  which validates the name (via `assert`, so a `-O` deployment skips the
  check — still never feed it raw user input).

## Domain injection

- Build/extend domains with `fields.Domain` (`domain &= Domain(...)`), never
  by concatenating a user-provided list onto a security domain (a user could
  inject `['|', ...]` to widen access).

## Don't over-sudo

- `sudo()` is the top risk — review every use twice, especially in controllers
  and public methods, never use it to mask an access error. For each `sudo()`,
  confirm there is no attacker-controlled:
  - **read**: arbitrary model / record / field;
  - **create**: arbitrary model / values;
  - **write**: arbitrary model / record / values;
  - **search**: arbitrary model / domain / injection.
- Controllers: never `record.sudo().write(post)` with raw request params —
  whitelist keys (`{k: post[k] for k in ('name', 'email') if post.get(k)}`).
- Under `sudo()`, x2many `Command` payloads in `vals` execute with sudo **on
  the comodel** (unless it sets `_allow_sudo_commands = False`) — a sudo
  write with raw request values pivots the privilege into other models, so
  whitelist command lists too.
- Avoid sudo-computed `related` fields onto `ir.attachment` (arbitrary
  `attachment_id` → arbitrary file read). Prefer a plain `fields.Binary`, or
  create/search `ir.attachment` records so the ORM enforces its access rights.
- `with_user` / `with_company` switches must be intentional, not
  attacker-driven.

## Routes: auth, POST, CSRF

- Match `auth` to the route's exposure: a `public`/`none` route must not
  expose internal data or perform privileged writes.
- A route that writes must use `methods=['POST']`; on a `type='http'` route
  keep CSRF on (never `csrf=False`, except dedicated webhooks) —
  `jsonrpc`/`json2` routes have no token check by design, their protection is
  the JSON content type. State-changing logic on a **GET** route is a CSRF
  hole: an attacker can auto-submit a hidden form / crafted
  link and perform the action as the logged-in victim.
- Templates that POST must include `<input type="hidden" name="csrf_token"
  t-att-value="request.csrf_token()"/>`.

## Prevent XSS (escape on the way into the DOM)

- Reflected (script in URL/params) and stored (script saved by a
  low-privileged user) both execute with the victim's session — far more than
  `alert()`.
- Server/QWeb: render with `t-out` (escapes by default). `t-raw` no longer
  exists in either server QWeb or OWL — flag any occurrence as broken legacy
  code; the raw-HTML vector today is a `Markup`/`markup()` value reaching
  `t-out`. Build HTML by wrapping **literals** in `markupsafe.Markup` and
  formatting user content in (Markup auto-escapes; `escape()`/`html_escape`
  turns `str` into escaped `Markup`). f-strings defeat escaping
  (`Markup(f"<p>{x}</p>")`) — use `Markup("<p>{x}</p>").format(x=...)`.
  `_()` escapes when any argument is `Markup`, so keep HTML out of the
  literal. (`t-esc`: deprecated-but-escaping alias in OWL; server QWeb
  ignores it and renders nothing — a bug to flag, though not an XSS.)
- JS: the sinks are `el.innerHTML = …`, `insertAdjacentHTML`, and owl
  `markup()` on a non-literal — never feed them user/low-privilege strings.
  Escape with `htmlEscape` (`@odoo/owl`) or use the tagged-template form
  ``markup`<td>${name}</td>` `` (placeholders auto-escape; plain
  `markup(str)` marks raw HTML), use the `@web/core/utils/html` helpers
  (`setInnerHtml`, `htmlJoin`), or render through OWL `t-out`.
- **Escaping vs sanitizing**: escaping (TEXT→CODE) is always mandatory when
  mixing data with code, even for trusted data. Sanitizing (CODE→safer CODE)
  is only for **untrusted** CODE and only works **after** escaping (sanitizing
  raw TEXT corrupts it). `fields.Html`/`html_sanitize` options
  (e.g. `strip_classes`) tune the level.

## Open files with `file_open`, not `open`

- Never use the builtin `open()` on a path that can be influenced — it can
  read *or write* arbitrary files on the host (config, ssh keys, executable
  Python → RCE). Use `odoo.tools.file_open()`, which confines access to the
  addons paths, the Odoo root, and registered temporary directories. It
  refuses to *create* files but will open an existing one in write mode — it
  is a path confinement, not a write protection.

## `eval` is evil

- Never `eval`/`exec`. To parse data use `json.loads()` or
  `ast.literal_eval()`; only at worst `odoo.tools.safe_eval.safe_eval` with a
  constrained namespace, and only for trusted privileged users (it still
  gives broad capabilities, and plain `eval` allows
  `__import__('os').popen(...)` RCE; master's extra `--unsafe-policy`
  whitelist sandbox is observe-only by default).

## Don't return complex objects from model methods

- A public model method that **returns** a rich object (a crypto key, a
  backend handle) is exploitable from `safe_eval`'d code — server actions,
  automation rules: the evaluated code calls it and walks single-underscore
  internals (`._backend._ffi`) to read files or run code. (Dunders are
  blocked there, and over RPC the return dies in marshalling — safe_eval is
  the live vector.) Don't factor such logic into a model method if not
  needed; use a standalone module-level function, or dunder-prefix the
  method name — dunder names are unreachable from safe_eval, `_`-names over
  RPC.

## `getattr`/`setattr` are not your friends

- Don't access record fields by dynamic name with `getattr`/`setattr` — it
  exposes private attributes and methods (`__class__` → `__globals__` →
  `__import__` → RCE). Use `record[name]` (safe `__getitem__`); still
  validate the record id and field name, otherwise restrict.

## Never `pickle`

- Builtin `pickle` executes arbitrary code on load (via `__reduce__`). Never
  unpickle untrusted data; store/exchange with `json` (the framework no
  longer ships a restricted pickle wrapper).

## Timing attacks

- Compare secrets/tokens in constant time with `odoo.tools.consteq`, not `==`
  (which short-circuits and leaks length/content via timing). Better, look
  the token up in the database (`search([('access_token', '=', token)])`).

## Mutable default arguments

- Don't use mutable default parameters (`def f(x, vals=[])`); they persist
  across calls and can leak/accumulate data.
