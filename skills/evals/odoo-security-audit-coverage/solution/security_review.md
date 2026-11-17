# Security review: property_rental

Answer key of the synthetic task: every planted issue, then the correct
constructs that must not be reported. Paths are relative to
addons/property_rental.

## Findings

F01 High - security/ir.access.csv, access_rental_lease_portal_edit: portal
users get create and write on rental.lease. Fix: no c/u for portal; route
the edits a tenant may make through a controller that whitelists fields.

F02 High - security/ir.access.csv: the tenant domain is only on the read row
(access_rental_lease_portal_read); the edit row has no domain, and write never
checks read access, so a portal user can write any tenant's lease. Fix: carry
the tenant domain on every operation, or drop the edit row.

F03 Medium - security/ir.access.csv: rental.property and rental.lease have a
company_id but no company restriction row; users see other companies'
properties and leases. Fix: a group-less row with
['|', ('company_id', '=', False), ('company_id', 'in', company_ids)].

F04 High - models/rental_property.py, listing_api_token: the API token has no
groups, so every internal user reads it with search_read (and with it calls
/rental/listing/sync). Fix: groups='base.group_system' or
fields.NO_ACCESS.

F05 High - models/rental_lease.py, owner_bank_account: a related field is
computed as superuser; tenants cannot read properties, but property_id is
writable by the tenant (F01, F18), so a tenant points it at any property and
reads that owner's IBAN. Fix: related_sudo=False, or compute it for the
tenant's own lease only.

F06 High - models/rental_lease.py, contract_file: a sudo related field onto
ir.attachment through the writable contract_attachment_id: any attachment's
content is readable. Fix: a plain fields.Binary, or read the attachment with
the ORM's access rights.

F07 High - models/rental_lease.py, action_apply_discount: a public method,
callable over RPC with any percent, writes the rent with sudo. Fix: make it
private, or check the caller's rights and bound the percent, without sudo.

F08 Critical - models/rental_property.py, occupancy_report: order_by is
interpolated into SQL with an f-string, from a public method: SQL injection.
Fix: whitelist the order, or SQL.identifier, and make the method private.

F09 Medium - models/rental_property.py, occupancy_report: raw SQL reads every
property and lease regardless of access and company rules. Fix: _read_group,
or _search(...) with Query.select.

F10 Medium - models/rental_property.py, get_listing_signing_key: a public
method returns a private key object, reachable from safe_eval'd code (server
actions) and from RPC, and reads the system-only key with sudo. Fix: a
module-level function, or a private (dunder) method that never returns the
key object.

F11 Medium - models/rental_lease.py, check_access_token: the token is compared
with ==, a timing attack. Fix: odoo.tools.consteq, or search on the token.

F12 Medium - models/rental_lease.py, _prepare_notify_values: the mutable
default partner_ids=[] accumulates across calls, so each signed lease
notifies every earlier tenant. Fix: partner_ids=None.

F13 High - models/rental_lease.py, _post_signed_message: Markup(f"...") puts
the tenant's name in the chatter unescaped: stored XSS (the tenant edits
their name). Fix: Markup("...{}...").format(name).

F14 Critical - controllers/portal.py, /my/leases and
models/rental_lease.py, _filtered_by_rule: the rule request parameter goes to
eval: remote code execution for any logged-in user. Fix: no eval; a fixed
set of filters.

F15 High - controllers/portal.py, /my/leases: the filter parameter is put in
front of the tenant domain and searched with sudo: a leading '|' (e.g.
['|', ('id', '!=', 0)]) turns it into "anything OR own leases" and returns
every lease. Fix: whitelist the filters, Domain(...) & Domain(...), no sudo.

F16 Medium - controllers/portal.py, /my/leases/<id>/cancel: a state change on
a GET route: CSRF by link. Fix: methods=['POST'] with the CSRF token.

F17 High - controllers/portal.py, /my/leases/<id>/update: csrf=False on a
type='http' POST route that is not a webhook. Fix: keep CSRF.

F18 Critical - controllers/portal.py, /my/leases/<id>/update:
lease.sudo().write(post) with raw request parameters: the tenant sets the
rent, state, property, tenant, and x2many commands as superuser. Fix:
whitelist the keys (notes), no sudo.

F19 Critical - controllers/portal.py, /my/leases/<id>/value: getattr on the
record with a request-chosen name exposes private attributes and methods.
Fix: lease[field] on a whitelist of field names.

F20 Critical - controllers/portal.py, /rental/record: sudo read of any model,
record and fields chosen by the request. Fix: remove, or a fixed model and
fields under the user's rights.

F21 High - controllers/portal.py, /rental/properties: an auth='public' route
returns owners and IBANs to anonymous visitors. Fix: auth='user' and only
public fields.

F22 High - controllers/portal.py, /rental/lease/sign: with_user takes the user
id from the request: the caller signs as any user. Fix: no with_user from
request data.

F23 Critical - controllers/portal.py, /rental/contract: open() on a path
built from the request: path traversal, reads any file. Fix: file_open and a
whitelist of contract names.

F24 Critical - controllers/portal.py, /rental/listing/sync: pickle.loads on
the request payload: remote code execution. Fix: json.

F25 Medium - views/portal_templates.xml, portal_my_leases: the POST form has
no csrf_token input. Fix: <input type="hidden" name="csrf_token"
t-att-value="request.csrf_token()"/>.

F26 Low - views/portal_templates.xml, portal_my_leases: t-raw no longer
exists; the notes are not rendered (broken legacy code). Fix: t-out.

F27 Low - views/portal_templates.xml, portal_my_leases: t-esc renders nothing
in server QWeb: the rent is missing (a bug, not an XSS). Fix: t-out.

F28 High - static/src/js/lease_notes.js: innerHTML set from the tenant-written
notes: stored XSS. Fix: textContent, or escape.

## Correct constructs (not findings)

- models/rental_property.py, _compute_active_lease_count: SQL composed with
  SQL and _search(...).select(...): parameterized, access rules applied.
- models/rental_lease.py, _compute_property_name: a commented sudo reading
  only the property name.
- controllers/portal.py, /rental/listing/sync: csrf=False on a token
  webhook, token compared with consteq (the pickle in it is F24).
- models/rental_property.py, listing_signing_key: the field itself is
  restricted to base.group_system (the method reading it with sudo is F10).
