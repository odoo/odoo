# Controllers

- Routes are methods decorated with `@route` on a `http.Controller` subclass.
  Always re-decorate an **override** with `@route` (an undecorated override
  still works — the framework auto-decorates it and logs a warning). An empty
  `@route()` keeps the parent's arguments and any argument overrides the
  parent's — except `type`, which an override can never change (ignored with
  a warning; loosening `readonly` is likewise reverted).
- Set the right `auth` on each route (`user`, `bearer`, `public`, or `none`):
  a `public` route must not expose internal data or perform privileged writes
  (see the `odoo-security` skill). `auth='bearer'` requires `bearer_scope`
  (which is only valid there).
- Route `type` is `'http'`, `'jsonrpc'`, or `'json2'` — `type='json'` is a
  deprecated 19.0 alias of `'jsonrpc'`.
