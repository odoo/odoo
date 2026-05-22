# HTTP Controller Pattern

**Purpose:** Expose server-side endpoints over HTTP using Odoo's routing layer (built on Werkzeug). Controllers handle web requests, JSON-RPC calls, portal pages, and REST-like API routes. They live in `controllers/` within an addon.

**Source:** `odoo/http.py`, `addons/calendar/controllers/main.py`, `addons/auth_signup/controllers/main.py`

---

## When to Use

- Serving a web page (portal, website, public route)
- Handling JSON-RPC calls from the JavaScript frontend (`type='jsonrpc'`)
- Building a REST endpoint consumed by external systems
- Processing form submissions or file uploads

---

## Basic Structure

```python
# addons/my_addon/controllers/main.py
from odoo import http
from odoo.http import request


class MyController(http.Controller):
    """All route methods live in a class inheriting http.Controller."""

    @http.route('/my/route', type='http', auth='public', website=True)
    def my_page(self, **kwargs):
        """Render an HTML page."""
        values = {
            'records': request.env['my.model'].sudo().search([]),
        }
        return request.render('my_addon.template_xmlid', values)
```

---

## Route Types

### type='http' — HTML Response

```python
# addons/calendar/controllers/main.py (lines 9–83)

class CalendarController(http.Controller):

    @http.route('/calendar/meeting/view', type='http', auth="calendar")
    def view_meeting(self, token, id, **kwargs):
        attendee = request.env['calendar.attendee'].sudo().search([
            ('access_token', '=', token),
            ('event_id', '=', int(id)),
        ])
        if not attendee:
            return request.not_found()

        lang = attendee.partner_id.lang or get_lang(request.env).code
        event = request.env['calendar.event'].with_context(
            tz=timezone, lang=lang
        ).sudo().browse(int(id))

        # Render a QWeb template
        response_content = request.env['ir.ui.view'].with_context(lang=lang)\
            ._render_template('calendar.invite_attendee_template', {'event': event})
        return request.make_response(
            response_content,
            headers=[('Content-Type', 'text/html')]
        )

    @http.route('/calendar/meeting/join', type='http', auth="user", website=True)
    def join_meeting(self, token, id, **kwargs):
        event = request.env['calendar.event'].sudo().search([
            ('access_token', '=', token)
        ])
        if not event:
            return request.not_found()
        return request.redirect('/odoo/calendar/%s' % event.id)
```

### type='jsonrpc' — JSON Response

```python
# addons/calendar/controllers/main.py (lines 96–119)

class CalendarController(http.Controller):

    @http.route('/calendar/notify', type='jsonrpc', auth="user")
    def notify(self):
        """Returns a Python value; Odoo serializes it to JSON automatically."""
        return request.env['calendar.alarm_manager'].get_next_notif()

    @http.route('/calendar/notify_ack', type='jsonrpc', auth='user')
    def notify_ack(self):
        return request.env['res.partner'].sudo()._set_calendar_last_notif_ack()

    @http.route('/calendar/check_credentials', type='jsonrpc', auth='user')
    def check_calendar_credentials(self):
        return request.env['res.users'].check_calendar_credentials()
```

---

## @http.route Parameters

| Parameter | Values | Purpose |
|-----------|--------|---------|
| `type` | `'http'`, `'jsonrpc'` | Response protocol |
| `auth` | `'public'`, `'user'`, `'none'`, custom token | Authentication level |
| `methods` | `['GET']`, `['POST']`, `['GET', 'POST']` | Allowed HTTP verbs |
| `website` | `True` / `False` | Inject website context (theme, lang, pricelist) |
| `csrf` | `True` (default) / `False` | CSRF token validation on POST |
| `cors` | `'*'` or origin string | CORS header for cross-origin JS calls |

---

## The `request` Object

```python
# Key attributes available inside any route method
request.env          # ORM environment (uid, context, cr)
request.env.user     # Current user record
request.env.company  # Current company

request.params       # Merged GET + POST params dict
request.httprequest  # Underlying Werkzeug Request object
request.session      # Session dict (uid, context, etc.)

# Common response helpers
request.render('addon.template_id', values)   # QWeb → HTML Response
request.redirect('/path')                      # HTTP 302
request.not_found()                            # HTTP 404
request.make_response(body, headers=[...])     # Raw response
```

---

## Inheritance / Extension

```python
# Extend an existing controller from another addon
from odoo.addons.auth_signup.controllers.main import AuthSignupHome

class MyExtendedController(AuthSignupHome):

    @http.route()   # Re-use parent's route definition; no args needed
    def web_login(self, *args, **kw):
        # Add pre/post logic around the parent implementation
        result = super().web_login(*args, **kw)
        return result
```

---

## controllers/__init__.py

```python
# addons/my_addon/controllers/__init__.py
from . import main
```

---

## Common Pitfalls

- **`sudo()` scope creep:** Using `.sudo()` bypasses all record rules. Narrow it to the minimum: fetch with `sudo()`, then operate with the user's env where possible.
- **`type='jsonrpc'` does not return HTTP errors naturally** — raise `odoo.exceptions.UserError` or `ValidationError`; the RPC layer converts them to JSON error objects.
- **Missing `csrf=False` on public POST endpoints** — Odoo enforces CSRF by default. External webhooks or REST consumers must either send the token or set `csrf=False` explicitly.
- **Route conflicts:** If two addons define the same path, the last-loaded one wins silently. Use addon-namespaced paths (`/my_addon/action`) to avoid collisions.
- **`auth='none'` vs `auth='public'`** — `'none'` skips all auth setup (no `request.env`). `'public'` creates an env as the public user. Use `'none'` only for health-check or static-like endpoints.
- **`website=True` adds overhead** — it fetches the current website record, theme, and pricelist. Only use it when rendering website-themed pages.

---

## Related Patterns

- [module-addon-structure-pattern.md](./module-addon-structure-pattern.md) — where controllers live
- [security-model-pattern.md](./security-model-pattern.md) — auth groups and portal access
- [owl-component-pattern.md](./owl-component-pattern.md) — frontend JS that calls `type='jsonrpc'` routes
