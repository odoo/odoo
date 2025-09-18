=================
Coding Guidelines
=================

This is the coding standard for the AgroMarin Odoo 19.0 **fork**. The fork exists to
continuously increase **code quality, maintainability, performance, and to adopt
cutting-edge features**. These guidelines evolve in that direction: when upstream Odoo
conventions conflict with higher quality or modern best practices, this document takes
precedence.

Based on the
`official Odoo coding guidelines <https://www.odoo.com/documentation/19.0/contributing/development/coding_guidelines.html>`_
and extended where noted. Improvements belong in ``core/`` first; ``addons_custom/`` is
reserved for business-specific AgroMarin needs that don't belong in a general-purpose
framework.

Automated enforcement is provided by ``core/ruff.toml``:

- **Linter**: ``ruff check`` — catches bugs, enforces imports, style, performance patterns.
- **Formatter**: ``ruff format`` — enforces consistent whitespace, quotes, line wrapping.
  Produces identical output to ``black``; both tools can coexist.
- **Auto-fix**: ``ruff check --fix`` — applies safe automatic corrections.

Target Python version: **3.14+** (see ``target-version`` in ``ruff.toml``).

Everything in this document that **can** be checked by tooling **is** checked — what
remains here is the guidance that tooling cannot enforce.

.. contents:: Table of Contents
   :depth: 2
   :local:


Module Structure
================

Standard directory layout for an Odoo module::

   module_name/
   ├── __init__.py
   ├── __manifest__.py
   ├── hooks.py               # pre_init_hook, post_init_hook, uninstall_hook
   ├── controllers/
   ├── data/
   ├── demo/
   ├── i18n/
   ├── models/
   ├── report/
   ├── security/
   ├── static/
   │   ├── description/
   │   │   └── icon.png
   │   ├── lib/
   │   └── src/
   │       ├── css/
   │       ├── js/
   │       ├── scss/
   │       └── xml/
   ├── tests/
   ├── views/
   └── wizards/

File naming
-----------

- File names must contain only **lowercase alphanumerics and underscores**: ``[a-z0-9_]``.
- One model per file: ``sale_order.py`` defines ``sale.order``.
- View files mirror model files: ``sale_order_views.xml``.
- Demo data: ``sale_order_demo.xml``.
- Security files: ``ir.model.access.csv``, ``<model>_security.xml``.
- Wizard models go in ``wizards/``.


``__manifest__.py``
-------------------

.. code-block:: python

   {
       "name": "Module Title",
       "version": "19.0.1.0.0",
       "category": "Sales",
       "summary": "One-line description",
       "author": "Author Name",
       "license": "LGPL-3",
       "depends": ["base", "sale"],
       "data": [
           "security/ir.model.access.csv",
           "views/model_views.xml",
       ],
       "demo": [
           "demo/model_demo.xml",
       ],
       "installable": True,
   }

Key rules:

- **Version format**: ``{odoo_version}.x.y.z`` — *x* major (breaking), *y* minor (new
  feature), *z* patch (bug fix).
- **Remove empty keys** rather than including them with empty values.
- **No ``auto_install: True``** unless the module is a bridge between two independent
  modules (e.g. ``sale_crm`` bridges ``sale`` and ``crm``).
- **Demo data** goes in the ``demo`` key.
- **Minimal ``depends``**: list only direct dependencies, not transitive ones.
- **External dependencies** must be declared:

.. code-block:: python

   'external_dependencies': {
       'python': ['requests'],
       'bin': ['wkhtmltopdf'],
   },


Python
======

PEP 8
-----

Follow `PEP 8 <https://peps.python.org/pep-0008/>`_ with these project-specific notes:

- **Line length** is *not* hard-enforced (``E501`` is ignored in ``core/ruff.toml``), but
  aim for ≤ 120 characters. Break long lines at logical points.
- **Indentation**: 4 spaces, no tabs.
- **Quote style**: double quotes (enforced by ``ruff format``). The formatter normalizes
  all quotes automatically — no manual effort required.

Code complexity
---------------

**Cyclomatic complexity (enforced).** ``C90`` with ``max-complexity = 20`` in
``ruff.toml``. Methods exceeding this threshold are flagged by the linter. The limit is
higher than typical (10–15) because Odoo dispatch methods and form logic are
inherently branchy, but low enough to flag genuinely complex code for refactoring.

**Method body limit (~40 lines, human-reviewed).** The linter cannot measure line count,
so this is a code review guideline. If a method exceeds ~40 lines, extract sub-methods.
Exempt: ``setUpClass``, data-heavy ``create()`` calls with many field mappings.

**Comprehension complexity.** Limit comprehensions to one ``for`` clause and one ``if``
filter. Nested loops must use explicit ``for`` statements:

.. code-block:: python

   # Correct — single for, single filter
   active_names = [p.name for p in partners if p.active]

   # Wrong — nested comprehension, hard to read
   result = {k: v for d in dicts for k, v in d.items() if k not in seen}

   # Correct — explicit loops for complex logic
   result = {}
   for d in dicts:
       for k, v in d.items():
           if k not in seen:
               result[k] = v

**No mutable default arguments.** Use the ``None`` sentinel pattern:

.. code-block:: python

   # Wrong — mutable default shared across calls
   def _prepare_values(self, vals={}):
       ...

   # Correct
   def _prepare_values(self, vals=None):
       if vals is None:
           vals = {}
       ...

**Use** ``match/case`` **for dispatch chains.** Replace long ``if/elif`` chains in
state machines, field-type dispatch, and operator routing:

.. code-block:: python

   match field.type:
       case 'many2one':
           return self._process_relational(field)
       case 'one2many' | 'many2many':
           return self._process_x2many(field)
       case 'monetary':
           return self._process_monetary(field)
       case _:
           return self._process_simple(field)

Imports
-------

Enforced by ``core/ruff.toml`` isort configuration. The order is:

1. Standard library (``import json``, ``from datetime import date``)
2. Third-party libraries (``from lxml import etree``)
3. Odoo core (``from odoo import api, fields, models``)
4. Local addons (``from odoo.addons.sale import ...``)

Within each group, sort alphabetically. Separate groups with a blank line.

.. code-block:: python

   import json
   from datetime import date, timedelta

   from lxml import etree

   from odoo import _, api, fields, models
   from odoo.exceptions import UserError, ValidationError
   from odoo.tools import float_compare

   from odoo.addons.account.models.account_move import AccountMove

Relative imports are permitted throughout the codebase (``TID252`` is suppressed in
``ruff.toml``). They are most common in ``__init__.py`` files but acceptable elsewhere
when they avoid circular dependencies or improve clarity.

For optional external libraries, guard imports to avoid blocking startup:

.. code-block:: python

   import logging
   _logger = logging.getLogger(__name__)

   try:
       import external_lib
   except ImportError:
       _logger.debug("external_lib not installed")
       external_lib = None


Lazy imports
~~~~~~~~~~~~

**All imports must be at module level unless there is a documented reason.**
Placing imports inside functions hides dependencies, duplicates code across methods,
and prevents tools from analyzing the module graph. ``PLC0415`` (import-outside-top-level)
is globally suppressed in ``ruff.toml`` because Odoo's architecture requires frequent lazy
imports. When a lazy import is necessary, include a **brief comment** explaining why:

Acceptable reasons for lazy imports:

1. **Circular dependency** that cannot be resolved by restructuring (e.g.
   ``odoo.tools`` importing from ``odoo.fields``):

   .. code-block:: python

      def json_default(obj):
          from odoo import fields  # circular: tools→fields
          ...

2. **Optional external dependency** (guarded with ``try``/``except ImportError``).

3. **Startup performance** in CLI entry points — deferring heavy Odoo imports so
   that ``--help`` stays fast.

4. **Namespace package** ``import odoo.addons`` — its ``__path__`` is populated
   dynamically by ``initialize_sys_path()``.

5. **Addon model imports from framework code** — model classes are not registered
   at framework import time.

**Not acceptable reasons:** "just in case", precautionary laziness, or the same import
repeated in multiple functions of the same file (a strong signal it should be at
module level).

**Detection rule:** if an import appears in two or more functions in the same file,
investigate whether it can be promoted. If the dependency direction allows it, move
it to the top.


Class attribute ordering
------------------------

Within a model class, declare attributes in this order:

1. Private attributes (``_name``, ``_description``, ``_inherit``, ``_order``, ``_rec_name``)
2. Index and constraint declarations (``models.Index``, ``models.Constraint``, ``models.UniqueIndex``)
3. Default method definitions
4. Field declarations
5. Compute, inverse, and search methods
6. Selection method definitions
7. Constraint methods (``@api.constrains``)
8. Onchange methods (``@api.onchange``)
9. CRUD method overrides (``create``, ``write``, ``unlink``, ``copy``)
10. Action methods (``action_confirm``, ``action_cancel``, ...)
11. Business methods

.. code-block:: python

   class SaleOrder(models.Model):
       _name = "sale.order"
       _description = "Sales Order"
       _inherit = ["mail.thread", "mail.activity.mixin"]
       _order = "date_order desc, id desc"

       # --- Indexes & Constraints ---
       _partner_date_idx = models.Index("(partner_id, date_order)")
       _name_uniq = models.Constraint(
           "unique(name, company_id)",
           "Order reference must be unique per company!",
       )

       # --- Fields ---
       name = fields.Char(string="Order Reference", required=True, readonly=True)
       partner_id = fields.Many2one("res.partner", string="Customer", required=True)
       line_ids = fields.One2many("sale.order.line", "order_id", string="Order Lines")
       amount_total = fields.Monetary(compute="_compute_amount_total", store=True)
       state = fields.Selection([
           ("draft", "Quotation"),
           ("sale", "Sales Order"),
           ("cancel", "Cancelled"),
       ], default="draft")

       # --- Compute ---
       @api.depends("line_ids.price_subtotal")
       def _compute_amount_total(self):
           for order in self:
               order.amount_total = sum(order.line_ids.mapped("price_subtotal"))

       # --- Constraints ---
       @api.constrains("line_ids")
       def _check_line_ids(self):
           for order in self:
               if not order.line_ids:
                   raise ValidationError(_("An order must have at least one line."))

       # --- CRUD ---
       @api.model_create_multi
       def create(self, vals_list):
           for vals in vals_list:
               if not vals.get("name") or vals["name"] == _("New"):
                   vals["name"] = self.env["ir.sequence"].next_by_code("sale.order")
           return super().create(vals_list)

       # --- Actions ---
       def action_confirm(self):
           self.write({"state": "sale"})

       # --- Business ---
       def _prepare_invoice(self):
           self.ensure_one()
           ...


Naming conventions
------------------

.. note::

   Most ``pep8-naming`` (N) rules are **suppressed** in ``ruff.toml`` because Odoo
   conventions conflict with PEP 8 (lowercase model classes, ``camelCase`` API methods,
   ``vals``/``cr``/``uid`` arguments). Two rules **remain enforced**: ``N804`` (first
   argument of class methods must be ``cls``) and ``N805`` (first argument of methods
   must be ``self``). All other naming is **human-reviewed**.

**Models:**

- Class name in ``PascalCase``: ``SaleOrder``, ``ResPartner``.
- ``_name`` in dotted ``lowercase``: ``sale.order``, ``res.partner``.

**Fields:**

- ``snake_case``: ``customer_name``, ``is_active``.
- ``Many2one`` fields **must** end with ``_id``: ``partner_id``, ``company_id``.
  No exceptions — fields like ``partner`` or ``company`` are violations.
- ``One2many`` and ``Many2many`` fields **must** end with ``_ids``: ``line_ids``,
  ``tag_ids``. No exceptions.
- Boolean fields **must** start with ``is_`` or ``has_``: ``is_locked``,
  ``has_attachments``. The only exception is ``active`` (Odoo framework magic field).
- Date fields end with ``_date``: ``delivery_date``, ``due_date``.
- Omit redundant ``string`` parameters — if the ``string`` would just be the field name
  in title case, leave it out. The ORM generates it automatically.

**Methods:**

- Computed field methods: ``_compute_<field_name>``
- Search methods: ``_search_<field_name>``
- Default methods: ``_default_<field_name>``
- Onchange methods: ``_onchange_<field_name>``
- Constraint methods: ``_check_<constraint_name>``
- Action methods: ``action_<name>``
- Private/internal methods: ``_<descriptive_name>``

**Variables:**

- ``snake_case`` for all variables.
- Recordsets: use the model name or a descriptive plural (``orders``, ``partners``).
- Single records: singular form (``order``, ``partner``).
- Use ``_logger`` for the module logger.


Common patterns
----------------

**Display names:**

.. code-block:: python

   @api.depends('name', 'code')
   def _compute_display_name(self):
       for record in self:
           record.display_name = f"{record.name} ({record.code})"

**Declarative indexes and constraints:**

.. code-block:: python

   # Regular composite index
   _partner_state_idx = models.Index("(partner_id, state)")

   # Simple unique constraint
   _code_uniq = models.Constraint(
       'unique(code, company_id)',
       'Code must be unique per company!',
   )

   # Partial unique index (with WHERE clause)
   _event_uniq = models.UniqueIndex(
       '(state_id, event_id) WHERE event_id IS NOT NULL',
       'Event must be unique per state!',
   )

**Computed stored fields with user override:**

.. code-block:: python

   fiscal_position_id = fields.Many2one(
       'account.fiscal.position',
       compute='_compute_fiscal_position_id',
       store=True,         # persisted to DB, enables search/filter
       readonly=False,     # allows manual user override
       precompute=True,    # computes before DB insertion
   )

**Command class for relational field operations:**

.. code-block:: python

   from odoo.fields import Command

   order.write({'line_ids': [
       Command.create({'product_id': product.id, 'quantity': 1}),
       Command.update(line_id, {'quantity': 5}),
       Command.delete(old_line_id),
   ]})

   partner.write({'category_id': [
       Command.link(tag.id),
       Command.unlink(old_tag.id),
       Command.set(tag_ids),
       Command.clear(),
   ]})

**Hooks:**

.. code-block:: python

   def post_init_hook(env):
       env['res.config.settings'].set_values({'setting': True})

**Multi-company records:**

.. code-block:: python

   company_id = fields.Many2one('res.company', index=True, required=True,
                                default=lambda self: self.env.company)

   # Company-dependent properties (value varies per company)
   barcode = fields.Char(company_dependent=True)

- Access the current company via ``self.env.company`` (not ``self.env.user.company_id``).
- Company domains should include ``False`` to match company-agnostic records:
  ``[('company_id', 'in', [company.id, False])]``.
- Implement ``_check_company_domain(self, companies)`` for custom company filtering.

**Wizards (TransientModel):**

.. code-block:: python

   class ConfirmOrderWizard(models.TransientModel):
       _name = 'sale.order.confirm.wizard'
       _description = "Confirm Orders"

       order_ids = fields.Many2many('sale.order')

       @api.model
       def default_get(self, fields_list):
           res = super().default_get(fields_list)
           if self.env.context.get('active_model') == 'sale.order':
               res['order_ids'] = [Command.set(self.env.context.get('active_ids', []))]
           return res

       def action_confirm(self):
           self.order_ids.action_confirm()
           return {'type': 'ir.actions.act_window_close'}

- Store wizard files in ``wizards/``.
- Populate from ``active_ids``/``active_model`` context keys via ``default_get()``.
- Use a ``state`` selection field for multi-step wizards.
- Return ``{'type': 'ir.actions.act_window_close'}`` to close the wizard dialog.


Controllers
~~~~~~~~~~~

HTTP controllers inherit from ``http.Controller`` and use the ``@route()`` decorator:

.. code-block:: python

   from odoo import http
   from odoo.http import request

   class SaleController(http.Controller):
       @http.route('/shop/cart', type='http', auth='public', methods=['GET'], website=True)
       def cart(self):
           order = request.website.sale_get_order()
           return request.render('website_sale.cart', {'order': order})

       @http.route('/api/orders', type='jsonrpc', auth='bearer', methods=['POST'])
       def create_order(self, **kwargs):
           order = request.env['sale.order'].create(kwargs)
           return {'id': order.id}

Key ``@route()`` parameters:

- ``type``: ``'http'`` (HTML/binary responses) or ``'jsonrpc'`` (JSON-RPC).
- ``auth``: ``'user'`` (authenticated, default), ``'public'`` (anonymous allowed),
  ``'bearer'`` (API token), ``'none'`` (no database).
- ``methods``: HTTP verbs (``['GET']``, ``['POST']``, etc.).
- ``csrf``: CSRF protection (default ``True`` for ``http``, ``False`` for ``jsonrpc``).

Response helpers: ``request.render(template, values)``,
``request.make_response(data, headers)``, ``request.redirect(url)``.

To override a route in an inheriting module, re-declare it with ``@route()`` on
the overriding method.


ORM best practices
------------------

**Always call ``super()``.**
``create()``, ``write()``, ``unlink()``, ``copy()``, ``default_get()``, and
``_compute_display_name()`` must always call ``super()``.

**Let the framework manage transactions.**
The framework handles ``cr.commit()`` and ``cr.rollback()`` for RPC calls, tests,
and cron jobs. The only exception is when you create your own cursor with
``self.env.registry.cursor()``.

**Assign fields directly in compute methods.**
Use ``self.field_name = value`` in ``_compute_*`` methods, as ``write()`` would cause
infinite recursion.

**Use ``ensure_one()``.**
Call ``self.ensure_one()`` at the start of methods that expect a single record:

.. code-block:: python

   def action_confirm(self):
       self.ensure_one()
       ...

**Use ``@api.ondelete`` for deletion constraints:**

.. code-block:: python

   @api.ondelete(at_uninstall=False)
   def _unlink_if_draft(self):
       if self.state != 'draft':
           raise UserError(_("Cannot delete a confirmed order."))

**Propagate context.**
Use ``with_context()`` to pass information through method calls — ``self.env.context``
is a frozen dict.

.. code-block:: python

   order.with_context(force_company=company.id).action_confirm()

**Catch only specific exceptions.**
Catch the narrowest exception that makes sense. Use ``odoo.exceptions.UserError``
for user-facing errors.

**Use recordset methods.**
Prefer ``filtered``, ``mapped``, ``sorted`` over manual loops when operating on
recordsets.

.. code-block:: python

   confirmed = orders.filtered(lambda o: o.state == 'sale')
   totals = orders.mapped('amount_total')
   by_date = orders.sorted('date_order')

**Use ``odoo.tools.groupby``.**
Handles recordsets correctly and does not require pre-sorting.

**Think extendable.**
Design models and methods so other modules can inherit and extend behavior without
patching. Avoid hardcoding values that could be configuration.

**Deprecate with** ``@api.deprecated``.
When replacing a method, use the decorator to emit runtime warnings and set the
``__deprecated__`` attribute for introspection:

.. code-block:: python

   @api.deprecated("Since 19.0, use _prepare_invoice_values instead")
   def _prepare_invoice(self):
       return self._prepare_invoice_values()


Error handling
--------------

Use the most specific exception type:

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Exception
     - When to Use
   * - ``UserError``
     - Business logic violations visible to the user: invalid state transitions,
       duplicate records, missing prerequisites.
   * - ``ValidationError``
     - Data constraint failures in ``@api.constrains`` methods.
   * - ``AccessError``
     - Permission or security violations (HTTP 403).
   * - ``RedirectWarning``
     - Errors resolvable by navigating to another view. Pass an action ID and
       button label.
   * - ``MissingError``
     - Record has been deleted or is inaccessible.
   * - ``ValueError``
     - Invalid arguments in internal/private methods (not user-facing).

All user-facing error messages **must** use ``_()``:

.. code-block:: python

   raise UserError(_("Order %s cannot be confirmed.", order.name))
   raise RedirectWarning(
       _("Please configure a default warehouse."),
       action_id, _("Go to Settings"),
   )


Domain class
------------

Odoo 19.0 provides a ``Domain`` class for building domains programmatically:

.. code-block:: python

   from odoo.fields import Domain

   # Single condition
   domain = Domain('state', '=', 'draft')

   # Combine with operators
   combined = Domain('state', '=', 'draft') & Domain('partner_id', '!=', False)
   either = Domain('type', '=', 'out_invoice') | Domain('type', '=', 'out_refund')
   negated = ~Domain('active', '=', False)

   # Aggregate multiple domains
   Domain.AND([dom1, dom2, dom3])
   Domain.OR([dom1, dom2])

   # Constants
   Domain.TRUE    # matches everything
   Domain.FALSE   # matches nothing

Use the ``Domain`` class for dynamic domain construction in Python. The traditional
list format ``[('field', 'op', value)]`` is still valid for simple static domains in
XML and data files.


Recordset safety
----------------

**Check existence** after operations that may delete records:

.. code-block:: python

   records = records.exists()  # filters out deleted records from the set

**Handle empty recordsets** — recordsets are falsy when empty:

.. code-block:: python

   partner = self.env['res.partner'].search([...], limit=1)
   if not partner:
       return  # no record found

   # Single-record guarantee
   self.ensure_one()

**Use** ``exists()`` after ``browse()`` when the record may not exist:

.. code-block:: python

   record = self.env['sale.order'].browse(record_id).exists()
   if not record:
       raise MissingError(_("Record %s has been deleted.", record_id))


Context management
------------------

The environment context (``self.env.context``) is a frozen dict. Use ``with_context()``
to pass information through method calls:

.. code-block:: python

   # Add/override keys
   records.with_context(force_company=company.id).action_confirm()

   # Read context
   lang = self.env.context.get('lang', 'en_US')

Common context keys:

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Key
     - Effect
   * - ``active_test``
     - When ``False``, includes archived (``active=False``) records in searches.
       Default is ``True``.
   * - ``lang``
     - Forces a specific language for translations and field values.
   * - ``tz``
     - Forces a timezone for datetime formatting.
   * - ``default_<field>``
     - Sets a default value for ``<field>`` on new records.
   * - ``active_ids``
     - List of record IDs from the source view (used by wizards and server actions).
   * - ``active_model``
     - Model name of the source records.
   * - ``tracking_disable``
     - When ``True``, disables mail tracking on ``write()`` (bulk imports).

Fields can declare context that is applied when the relational field is accessed:

.. code-block:: python

   child_ids = fields.One2many('res.partner', 'parent_id', context={'active_test': False})


Monetary fields
---------------

``fields.Monetary`` requires a companion currency field. By default it looks for
``currency_id`` on the same model:

.. code-block:: python

   currency_id = fields.Many2one('res.currency', required=True)
   amount_total = fields.Monetary()

   # If the currency field has a different name:
   base_currency_id = fields.Many2one('res.currency')
   amount_in_base = fields.Monetary(currency_field='base_currency_id')

The ORM uses the currency for rounding, display formatting, and aggregation.
Omitting the currency field raises a runtime error.


Translations
------------

Wrap user-facing strings with ``_()``. Pass arguments separately so the translation
system can process the template string:

.. code-block:: python

   raise UserError(_("Order %s cannot be confirmed.", order.name))

Use ``_lt()`` (lazy translation) for module-level constants evaluated at import time:

.. code-block:: python

   from odoo import _lt

   STATUS_LABELS = {
       'draft': _lt("Draft"),
       'confirmed': _lt("Confirmed"),
   }

Field ``string`` parameters are automatically translated by the framework.


String formatting
-----------------

- **Prefer f-strings** for general Python code: ``f"{name} ({code})"``.
  The linter (``FLY``) suggests f-string conversions where safe.
- **f-strings are fine in exceptions** — ``EM102`` is suppressed because pragmatic
  error messages outweigh the minor overhead:
  ``raise ValueError(f"Invalid mode: {mode!r}")``
- **Use** ``%s`` **inside** ``_()``: ``_("Order %s cannot be confirmed.", order.name)``.
  The translation system extracts the template string — f-strings inside ``_()`` silently
  break translations with no error raised.
- **Use** ``%s`` **in logging calls**: ``_logger.info("Processing %s records", count)``.
  Deferred formatting avoids string construction when the log level is disabled.
  Enforced by ``G`` (flake8-logging-format).
- **Use** ``%s`` **for SQL parameterization**: ``cr.execute("... WHERE id = %s", (rid,))``.
- **``%``-formatting is not auto-converted** — ``UP031`` is suppressed because ``%s`` is
  idiomatic in SQL, logging, and ``_()``. The linter does not distinguish these contexts,
  so the rule is globally disabled.

.. code-block:: python

   # Correct
   raise UserError(_("Cannot confirm order %s.", order.name))
   _logger.info("Imported %s records in %s seconds", count, elapsed)

   # Wrong — breaks translation extraction
   raise UserError(_(f"Cannot confirm order {order.name}."))
   _logger.info(f"Imported {count} records in {elapsed} seconds")


Datetime handling
-----------------

``datetime.utcnow()`` is deprecated since Python 3.12. Use ``datetime.now(UTC)``:

.. code-block:: python

   from datetime import UTC, datetime

   # Aware datetime (for comparisons, external APIs)
   now_aware = datetime.now(UTC)

   # Naive datetime (for ORM Datetime fields — Odoo stores UTC without tzinfo)
   now_naive = datetime.now(UTC).replace(tzinfo=None)

**Common pitfall:** comparing ``datetime.now(UTC)`` (aware) with an ORM field value
(naive) raises ``TypeError``. Strip ``tzinfo`` before comparing with ORM values.

The linter enforces this via ``DTZ003`` (``utcnow`` banned) and the ``banned-api``
section in ``ruff.toml``.


Markup in error messages
------------------------

Use ``Markup()`` from ``markupsafe`` for intentional HTML in user-facing messages:

.. code-block:: python

   from markupsafe import Markup

   raise UserError(Markup(_(
       "Invoice <b>%(name)s</b> cannot be confirmed.",
       name=invoice.name,
   )))

**Never use f-strings with** ``Markup()`` — user input would be injected as raw HTML
(XSS vulnerability). Always use ``%``-style or ``format()`` with ``Markup()`` so that
arguments are auto-escaped.


Code hygiene
------------

The following rules are **enforced by the linter** — violations are flagged automatically:

- **No** ``print()`` **in production code** (``T20``). Use ``_logger`` instead.
  ``print()`` is allowed in tests (suppressed via per-file-ignores).
- **No debugger statements** (``T10``). Remove ``breakpoint()``, ``pdb.set_trace()``,
  and ``import pdb`` before committing.
- **No commented-out code** (``ERA001``). Dead code should be deleted, not commented.
  The linter warns but does not auto-remove — requires human review. Use version control
  to recover old code if needed.
- **Prefer** ``pathlib.Path`` **over** ``os.path`` (``PTH``). The linter flags ``os.path``
  usage and suggests ``pathlib`` equivalents. Exceptions: ``tools/files.py`` (security-
  critical path validation) and migration scripts are exempt via per-file-ignores.
- **Prefer exception chaining** — use ``raise X from Y`` to preserve the original
  traceback when re-raising a different exception. ``B904`` is currently suppressed for
  legacy code, but **new code should always chain exceptions**:

.. code-block:: python

   # Preferred — preserves the original traceback
   try:
       value = int(user_input)
   except ValueError as e:
       raise UserError(_("Invalid number: %s", user_input)) from e

   # Acceptable only in legacy code (B904 suppressed)
   except ValueError:
       raise UserError(_("Invalid number: %s", user_input))


Docstrings
----------

Use triple double-quotes. First line is a brief imperative summary ending with a period.
For multi-line docstrings, add a blank line before parameters:

.. code-block:: python

   def _prepare_invoice_values(self, partner):
       """Prepare values for creating an invoice.

       :param partner: the customer to invoice
       :return: dictionary of invoice field values
       :rtype: dict
       """

- Compute methods: describe *what* is computed, not the implementation.
- One-liner docstrings: ``"""Return the tax amount for the given line."""``
- Use ``:param name: description``, ``:return: description``, ``:rtype: type``.
- Omit docstrings on trivial methods where the name is self-explanatory
  (e.g., ``_compute_display_name``).


Logging levels
--------------

.. list-table::
   :header-rows: 1
   :widths: 15 85

   * - Level
     - Use Case
   * - ``debug``
     - Development diagnostics, configuration loading, detailed execution flow.
       Only visible with explicit log-level setting.
   * - ``info``
     - Normal business events: module loading, batch completions, scheduled actions.
   * - ``warning``
     - Recoverable issues: deprecated usage, fallback behavior, missing optional config.
   * - ``error``
     - Failures requiring investigation: unhandled exceptions, data corruption,
       integration failures. Use ``exc_info=True`` to include the traceback.

.. code-block:: python

   _logger.debug("Cache miss for %s, fetching from DB", key)
   _logger.info("Imported %s records from CSV", count)
   _logger.warning("Field %s is deprecated, use %s instead", old, new)
   _logger.error("Payment gateway returned %s", status, exc_info=True)

For cross-model operations (invoicing, EDI, payment processing), include a correlation
identifier so all log entries from a single business transaction can be traced:

.. code-block:: python

   _logger.info("[order:%s] Starting invoice creation", order.name)
   _logger.info("[order:%s] PAC stamping completed, UUID: %s", order.name, uuid)


Type hints
----------

Type hints are optional. Use them where they improve clarity — especially on public
API methods, framework-level code, and complex return types:

.. code-block:: python

   from typing import TYPE_CHECKING

   if TYPE_CHECKING:
       from .res_users import ResUsers

   class ResPartner(models.Model):
       _name = "res.partner"

       user_ids: ResUsers = fields.One2many("res.users", "partner_id")

       def _find_matching_partner(self, email: str) -> ResPartner | None:
           ...

Guard ``TYPE_CHECKING`` imports to avoid circular imports at runtime. Python 3.14's
deferred annotation evaluation (PEP 649) means forward references like
``-> ResPartner | None`` work without string quoting.

**Use** ``@typing.override`` **on method overrides** (Python 3.12+). Apply to
``create()``, ``write()``, ``unlink()``, ``_compute_*``, and any overridden parent
method. This catches silent breakage when a parent method is renamed:

.. code-block:: python

   from typing import override

   class SaleOrder(models.Model):
       _inherit = 'sale.order'

       @override
       def action_confirm(self):
           ...
           return super().action_confirm()


Security
========

Method visibility
-----------------

Public methods (no underscore prefix) are callable via XML-RPC/JSON-RPC by any
authenticated user. ACL checks only happen during CRUD operations — custom public
methods do **not** automatically enforce access rules.

- **Default all methods to private** (prefix with ``_``). Remove the underscore only
  after deliberate review.

``sudo()`` discipline
---------------------

- Whitelist which fields are allowed when writing user-submitted payloads.
- Minimize scope — apply ``sudo()`` to the smallest recordset and fewest operations.
- Every ``sudo()`` call should be flagged for review.

.. code-block:: python

   def action_update(self, values):
       allowed = {'description', 'tag_ids'}
       safe_vals = {k: v for k, v in values.items() if k in allowed}
       self.sudo().write(safe_vals)

Input validation
-----------------

``assert`` statements are stripped when Python runs with ``-O`` (optimized mode).
Any validation that guards security-sensitive logic **must** use ``if``/``raise``
instead:

.. code-block:: python

   # Validate security-sensitive input
   if access_mode not in ('read', 'write', 'create', 'unlink'):
       raise ValueError(f"Invalid access mode: {access_mode!r}")

SQL injection prevention
------------------------

**All** dynamic SQL **must** use parameterized queries or the ``SQL`` wrapper.
f-strings, ``.format()``, and ``%`` formatting on query strings are violations —
even when the values come from ORM metadata like ``_table`` or ``field.name``.
Use the ``SQL`` wrapper for defense-in-depth:

.. code-block:: python

   from odoo.tools import SQL

   # Parameterized values
   self.env.cr.execute("SELECT id FROM res_partner WHERE name = %s", (name,))

   # SQL wrapper for dynamic identifiers (tables, columns)
   self.env.cr.execute(SQL(
       "SELECT id FROM %s WHERE %s = %s",
       SQL.identifier(model._table),
       SQL.identifier(field.name),
       value,
   ))

Related fields and ACLs
------------------------

Related fields are computed in ``sudo`` mode, bypassing access control. A related
field pointing to a sensitive model (``ir.attachment``, ``hr.payslip``) can leak
data. Prefer ``fields.Binary`` or controlled ``search()`` calls when accessing
protected records.

Controller security
-------------------

- ``auth='public'`` runs as the Public user, including unauthenticated visitors.
- ``auth='none'`` means no database access — mainly for framework use.
- Validate and sanitize all controller parameters.
- Use ``Markup()`` for intentional HTML output; escape user-generated content.

Fail-closed error handling
--------------------------

Exception handlers in state-mutation code **must** leave the system in a consistent
state. Use ``cr.savepoint()`` so partial operations roll back on failure:

.. code-block:: python

   for order in orders:
       try:
           with self.env.cr.savepoint():
               order._process_payment()
               order.action_confirm()
       except UserError:
           order.state = 'error'
           _logger.error("Failed to process order %s", order.name, exc_info=True)

``except Exception`` is flagged by the linter (``BLE001``). Use it only when genuinely
necessary (e.g., catch-log-reraise patterns, integration adapters). Always re-raise or
transition to an explicit error state — never silently swallow exceptions.

Broad ``except Exception`` blocks that log-and-continue are a violation in financial
or state-mutation code. Each failure must either roll back its changes or explicitly
transition to an error state.

Error information disclosure
----------------------------

**Never expose raw exceptions to users.** Internal error details (SQL fragments, Python
tracebacks, file paths) aid attackers:

.. code-block:: python

   # Wrong — leaks internals
   except Exception as e:
       raise UserError(str(e))

   # Correct — generic user message, full details in server log
   except Exception:
       _logger.error("Payment processing failed", exc_info=True)
       raise UserError(_("Payment could not be processed. Contact support."))

Configuration and secrets
--------------------------

- **No hardcoded URLs, credentials, or service endpoints** in Python code. Use
  ``ir.config_parameter``, environment variables, or ``odoo.conf`` for all external
  configuration.
- **External dependencies** must be declared in ``__manifest__.py``
  ``external_dependencies`` AND in a ``requirements.txt`` at the addon root.
  Pin minimum versions.

Deployment checklist
--------------------

Before production deployment, verify:

- ``--dev`` mode is disabled.
- ``list_db = False`` in configuration.
- Default admin password is changed.
- ``proxy_mode = True`` if behind a reverse proxy.
- ``dbfilter`` is set to restrict database access.
- ``server_wide_modules`` is minimal.
- Python dependencies are pinned with hashes. Run ``pip-audit`` in CI.


Performance
===========

Avoiding N+1 queries
--------------------

Any ``search()``, ``search_count()``, or ``_read_group()`` call inside a ``for``
loop over a recordset is a violation. Aggregate **outside** the loop with
``_read_group()``:

.. code-block:: python

   groups = self.env['child.model']._read_group(
       [('parent_id', 'in', records.ids)],
       groupby=['parent_id'],
       aggregates=['__count'],
   )
   count_map = {parent.id: count for parent, count in groups}
   for record in records:
       record.child_count = count_map.get(record.id, 0)

Use dictionary lookups to avoid nested loops:

.. code-block:: python

   lines_by_order = defaultdict(list)
   for line in all_lines:
       lines_by_order[line.order_id.id].append(line)
   for order in orders:
       for line in lines_by_order[order.id]:
           ...

Batch operations
----------------

- Use ``create()`` with a list of dicts (leverages ``@api.model_create_multi``)
  instead of calling ``create()`` in a loop.
- Use ``write()`` on a full recordset rather than iterating and writing individually.
- Use ``search_read()`` when you only need specific fields — more efficient than
  ``search()`` + ``read()``.
- **Use** ``search_count()`` **for counts** — never ``len(search(domain))``.
  ``search()`` instantiates all matching records in Python; ``search_count()``
  executes ``SELECT COUNT(*)`` server-side:

.. code-block:: python

   # Wrong — loads all records into memory
   count = len(self.env['account.move.line'].search(domain))

   # Correct — server-side count
   count = self.env['account.move.line'].search_count(domain)

   # For existence checks, use limit=1
   exists = bool(self.env['account.move.line'].search(domain, limit=1))

- **Use** ``_read_group()`` **for aggregation** — never Python-side ``sum()`` over
  recordsets. Push computation to PostgreSQL:

.. code-block:: python

   # Wrong — loads every record into Python
   total = sum(line.amount for line in self.env['account.move.line'].search(domain))

   # Correct — single SQL query
   [total] = self.env['account.move.line']._read_group(
       domain, aggregates=['amount:sum'],
   )

``search_fetch()``
------------------

Use ``search_fetch()`` when you need a recordset with specific fields pre-loaded.
It combines ``search()`` and field fetching in minimal queries — more efficient than
``search()`` followed by field access, and returns a proper recordset (unlike
``search_read()`` which returns dicts):

.. code-block:: python

   # Optimal — search + fetch specific fields in minimal queries
   orders = self.env['sale.order'].search_fetch(
       [('state', '=', 'sale')],
       ['partner_id', 'amount_total', 'date_order'],
       limit=100,
   )

Prefetching
-----------

Iterating a recordset triggers automatic prefetching for all records in the set.
This is efficient for standard iteration. Disable prefetching with ``with_prefetch([])``
for large single-record operations where you don't want the ORM to fetch all sibling
records:

.. code-block:: python

   for record in large_recordset.with_prefetch([]):
       record._heavy_processing()  # only fetches fields for this record

``ormcache``
------------

Use ``@ormcache`` for read-heavy, rarely-changing data: model metadata, view parsing
results, ACL lookups, configuration values.

.. code-block:: python

   from odoo.tools import ormcache

   @ormcache('self.env.uid', 'model_name')
   def _get_access_rights(self, model_name):
       """Return access rights dict. Must NOT return recordsets."""
       ...
       return rights_dict

**Critical constraint:** cached methods must **never return recordsets**. The database
cursor used to create the recordset will be closed on subsequent calls, causing
``InterfaceError``. Return plain Python types (dicts, lists, sets, tuples, scalars).

Invalidation: ``self.env.registry.clear_cache()`` clears all ormcache entries. The
ORM invalidates automatically on model changes via ``modified()``.

Computed fields
---------------

- Prefer ``store=True`` only when the field is used in search domains, ordering, or
  grouping. Non-stored computed fields avoid recomputation overhead on writes.
- **Every sub-field accessed in the method body must appear in** ``@api.depends``.
  Incomplete chains cause silent stale data. If the method reads
  ``record.partner_id.country_id``, then ``'partner_id.country_id'`` **must** be
  in the decorator — ``'partner_id'`` alone is not sufficient:

.. code-block:: python

   @api.depends('partner_id.country_id')
   def _compute_country(self):
       for rec in self:
           rec.country_id = rec.partner_id.country_id

- Verification rule: for every ``record.x_id.y`` read inside the method, confirm
  that ``'x_id.y'`` (not just ``'x_id'``) is listed in ``@api.depends``.
- **Exception — initialization-only computes**: when a ``store=True, readonly=False``
  computed field is designed to set an initial default (e.g., inheriting ``lang`` from
  parent on reparenting), a coarser dependency like ``'parent_id'`` is intentional.
  Using ``'parent_id.lang'`` would recompute and overwrite user edits whenever the
  parent's lang changes. Similarly, fields with an ``inverse`` that writes back to the
  same path must use a coarser dependency to avoid circular triggers.
- Avoid long chains of stored computed fields depending on each other — flatten
  dependencies when possible.

Indexing
--------

- Add ``index=True`` to fields used in ``search()`` domains, ``ORDER BY``, or
  ``GROUP BY``.
- Each index adds overhead to ``write`` and ``create`` — index selectively.
- Use ``models.Index()`` for composite indexes.

**Partial indexes** — for tables where most queries filter on a specific state, a
partial index is 10–50x smaller and faster than a full index:

.. code-block:: python

   # Only index non-done orders (the rows actually queried)
   _state_date_idx = models.Index("(date_order) WHERE state != 'done'")

**BRIN indexes** — for append-only or time-series tables (``mail.message``,
``ir.logging``, ``bus.bus``), BRIN indexes are 100–1000x smaller than B-tree:

.. code-block:: python

   _create_date_brin = models.Index("USING brin (create_date) WITH (pages_per_range=128)")

**Expression indexes** — for case-insensitive search on fields commonly queried with
``ilike``, add an expression index to avoid full table scans:

.. code-block:: python

   _name_upper_idx = models.Index("(UPPER(name))")

Raw SQL review
--------------

Any raw SQL added via ``cr.execute()`` **must** include an ``EXPLAIN ANALYZE`` output
in the pull request description, demonstrating that the query plan uses indexes
appropriately. This makes performance a code review gate.

Database flush and cache
------------------------

The ORM delays database writes for performance. Before executing raw SQL, ensure
consistency:

.. code-block:: python

   self.flush_model()         # write pending values to DB
   self.env.cr.execute(...)   # now raw SQL sees current data
   self.invalidate_model()    # refresh cache after direct SQL changes

Cron jobs and batch processing
-------------------------------

Scheduled actions processing large recordsets **must** use batch processing with
progress tracking. Call ``self.env['ir.cron']._commit_progress()`` to commit each
batch and report progress to the framework:

.. code-block:: python

   from itertools import batched

   def _cron_process_orders(self):
       orders = self.env['sale.order'].search([('state', '=', 'pending')])
       commit_progress = self.env['ir.cron']._commit_progress
       for batch_ids in batched(orders.ids, 100):
           batch = orders.browse(batch_ids)
           batch._process()
           remaining = commit_progress(
               processed=len(batch),
               remaining=len(orders) - len(batch),
           )
           if remaining <= 0:
               break  # time limit reached

- Process in batches (100–1000 records) using ``itertools.batched()`` to limit memory
  and lock duration. (``split_every`` is deprecated since 19.0.)
- Use ``self.env['ir.cron']._commit_progress(processed, remaining)`` — it calls
  ``cr.commit()`` internally and returns remaining execution time (seconds).
- Set ``deactivate=True`` on the final call for one-time cron jobs.
- **Do not** call ``cr.commit()`` directly — the framework manages it through
  ``_commit_progress()`` and the cron runner.

Concurrency and locking
------------------------

PostgreSQL row-level locking prevents concurrent modifications:

.. code-block:: python

   # Fail immediately if another transaction holds the lock
   self.env.cr.execute(SQL(
       "SELECT id FROM %s WHERE id = %s FOR UPDATE NOWAIT",
       SQL.identifier(self._table), self.id,
   ))

   # Skip locked rows (job queues, cron dispatching)
   self.env.cr.execute(SQL(
       "SELECT id FROM %s WHERE state = %s FOR UPDATE SKIP LOCKED",
       SQL.identifier(self._table), 'pending',
   ))

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Lock Mode
     - Use Case
   * - ``FOR UPDATE NOWAIT``
     - Critical sections (sequences, payment processing). Raises
       ``OperationalError`` if locked.
   * - ``FOR UPDATE SKIP LOCKED``
     - Job queues and cron dispatching. Silently skips locked rows.
   * - ``FOR NO KEY UPDATE``
     - When foreign key relationships are not affected by the update.

- Always handle ``OperationalError`` / ``LockError`` when using ``NOWAIT``.
- Minimize lock duration: lock → operate → commit as fast as possible.
- Prefer ORM-level ``search()`` with domain filters over table-level locks.


XML
===

File format
-----------

- Use **2-space indentation** for XML files.
- Place ``id`` before ``model`` in ``<record>`` tags.
- Place field ``name`` attribute first, then ``ref``/``eval``/text content.

.. code-block:: xml

   <record id="sale_order_view_form" model="ir.ui.view">
     <field name="name">sale.order.form</field>
     <field name="model">sale.order</field>
     <field name="arch" type="xml">
       <form string="Sales Order">
         ...
       </form>
     </field>
   </record>

View syntax
-----------

Use direct Python-like expressions for ``invisible``, ``readonly``, and ``required``:

.. code-block:: xml

   <field name="date" invisible="state in ('draft', 'cancel')" readonly="is_locked"/>
   <field name="amount" invisible="state == 'draft' or amount == 0"/>
   <button name="action_confirm" invisible="state != 'draft'"/>

Use ``<list>`` for list views and ``<chatter/>`` for the chatter widget.


XML ID naming
-------------

Follow these patterns for external identifiers:

.. list-table::
   :header-rows: 1
   :widths: 30 50 20

   * - Type
     - Pattern
     - Example
   * - Form view
     - ``<model_name>_view_form``
     - ``sale_order_view_form``
   * - List view
     - ``<model_name>_view_list``
     - ``sale_order_view_list``
   * - Kanban view
     - ``<model_name>_view_kanban``
     - ``sale_order_view_kanban``
   * - Search view
     - ``<model_name>_view_search``
     - ``sale_order_view_search``
   * - Action
     - ``<model_name>_action``
     - ``sale_order_action``
   * - Menu (root)
     - ``<model_name>_menu``
     - ``sale_order_menu``
   * - Menu (action)
     - ``<model_name>_menu_<action>``
     - ``sale_order_menu_list``
   * - Security group
     - ``<module>_group_<name>``
     - ``sale_group_manager``
   * - Record rule
     - ``<model_name>_rule_<group>``
     - ``sale_order_rule_portal``
   * - Server action
     - ``<model_name>_action_<name>``
     - ``sale_order_action_confirm``

The current module name is prefixed to XML IDs automatically.


View inheritance
----------------

Inherited views should use the original XML ID with ``.inherit.<module>`` appended.
Target XPath by ``name`` attribute for stability:

.. code-block:: xml

   <record id="sale_order_view_form.inherit.custom_module" model="ir.ui.view">
     <field name="name">sale.order.form.inherit.custom_module</field>
     <field name="model">sale.order</field>
     <field name="inherit_id" ref="sale.sale_order_view_form"/>
     <field name="arch" type="xml">
       <xpath expr="//field[@name='partner_id']" position="after">
         <field name="custom_field"/>
       </xpath>
     </field>
   </record>


JavaScript
==========

Static file organization
------------------------

::

   static/
   ├── lib/          # Third-party libraries (unminified source)
   ├── src/
   │   ├── js/       # Application JavaScript
   │   ├── css/      # Plain CSS
   │   ├── scss/     # SCSS stylesheets
   │   └── xml/      # QWeb templates
   └── tests/
       └── tours/    # Tour test files

General rules
-------------

- Always use ``"use strict";`` in JavaScript files.
- Include unminified source for third-party libraries in ``static/lib/``.
- Use ES6+ syntax: ``const``/``let``, arrow functions, template literals.
- Use ``PascalCase`` for class and component names.
- Use ``camelCase`` for variables, functions, and method names.
- Add JSDoc comments for public APIs and complex functions.
- Use ``t-esc`` for user-generated content in QWeb templates.


CSS and SCSS
============

Syntax and formatting
---------------------

- **4-space indentation**, no tabs.
- **80-character** maximum line width.
- One selector per line in multi-selector rules.
- One declaration per line.
- Space after the colon in declarations.
- Opening brace on the same line as the selector, closing brace on its own line.

.. code-block:: scss

   .o_sale_order_form {
       display: flex;
       margin: 0 auto;
       padding: $spacing-base;
       background-color: $color-bg;
       font-size: 14px;
   }


Property ordering
-----------------

Group CSS properties in this order:

1. SCSS variables
2. CSS custom properties (``--var``)
3. Position (``position``, ``top``, ``right``, ``bottom``, ``left``, ``z-index``)
4. Display and box model (``display``, ``flex-*``, ``grid-*``, ``float``, ``clear``)
5. Dimensions (``width``, ``height``, ``margin``, ``padding``)
6. Border (``border``, ``border-radius``, ``outline``)
7. Background (``background``, ``box-shadow``)
8. Typography (``color``, ``font-*``, ``text-*``, ``line-height``)
9. Effects (``opacity``, ``filter``, ``transform``, ``transition``, ``animation``)


Naming conventions
------------------

**CSS classes:**

- Prefix with ``o_<module_name>``: ``o_sale_order_form``, ``o_account_payment_btn``.
- Use the "grandchild" approach for nested elements — avoid deeply specific names.
- **Never** use IDs for styling.

**SCSS variables (global):**

- Format: ``$o-[root]-[element]-[property]-[modifier]``
- Examples: ``$o-sale-header-bg-color``, ``$o-form-field-height``

**SCSS variables (scoped):**

- Format: ``$-[name]``
- Declared near usage within a block.

**SCSS mixins and functions:**

- Format: ``o-[name]``
- Arguments: ``$-[argument]``
- Example: ``@mixin o-position-absolute($-top: 0, $-left: 0)``

**CSS custom properties:**

- Format: ``--[root]__[element]-[property]--[modifier]``
- Examples: ``--sale__header-bg-color``, ``--form__field-height--sm``

Use CSS custom properties for runtime theming and DOM-contextual adaptations.
Use SCSS variables for compile-time design system values and calculations.


Testing
=======

Test classes
------------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Base Class
     - Use Case
   * - ``TransactionCase``
     - Standard ORM tests. Each method runs in its own rolled-back transaction.
   * - ``SingleTransactionCase``
     - Tests sharing state across methods (same transaction).
   * - ``HttpCase``
     - Controllers, web UI, Chrome headless. Tag with ``@tagged('post_install', '-at_install')``.

Test isolation
--------------

- **Create all test records** in ``setUpClass()`` or the test method.
- **Use fixed dates** — ``datetime.now()`` creates flaky tests.
- **Mock external services** — tests must run offline.
- **Test with minimal permissions** — create a user with only the group being tested
  to catch access rule issues early.
- **Never call** ``cr.commit()`` **in tests**. All test data must be created within the
  test transaction and automatically rolled back. A committed transaction permanently
  pollutes the test database and causes cascading failures.

``setUpClass`` convention
~~~~~~~~~~~~~~~~~~~~~~~~

Use ``@classmethod def setUpClass(cls)`` for creating test records shared across test
methods in a class — this runs once per class, not once per method:

.. code-block:: python

   @classmethod
   def setUpClass(cls):
       super().setUpClass()
       cls.partner = cls.env['res.partner'].create({'name': 'Test Partner'})
       cls.product = cls.env['product.product'].create({'name': 'Test Product'})

Use ``setUp(self)`` only when per-method state reset is required (e.g., mutable state
that one test method may alter in a way that affects another).

``BaseCommon`` test mixin
~~~~~~~~~~~~~~~~~~~~~~~~~

``odoo.addons.base.tests.common.BaseCommon`` provides a standard test environment with
mail/tracking disabled, independent users and companies, and convenience helpers:

.. code-block:: python

   from odoo.addons.base.tests.common import BaseCommon

   class TestSaleOrder(BaseCommon):
       @classmethod
       def setUpClass(cls):
           super().setUpClass()
           # cls.company, cls.currency, cls.partner already available
           cls.order = cls.env['sale.order'].create({...})

Key features:

- ``DISABLED_MAIL_CONTEXT`` — disables tracking, mail notifications, and password resets
  during test setup for performance.
- Pre-created ``cls.company``, ``cls.currency``, ``cls.partner``, ``cls.group_*``.
- Helpers: ``quick_ref(xmlid)``, ``_create_partner()``, ``_create_new_internal_user()``,
  ``_create_new_portal_user()``.

Flush before raw SQL in tests
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When asserting on database state after ORM operations, call ``flush_model()`` or
``flush_recordset()`` before raw SQL queries:

.. code-block:: python

   def test_write_updates_database(self):
       self.order.write({'state': 'sale'})
       self.order.flush_recordset(['state'])
       self.env.cr.execute("SELECT state FROM sale_order WHERE id = %s", (self.order.id,))
       self.assertEqual(self.env.cr.fetchone()[0], 'sale')

Without flushing, the ORM may not have written pending values to the database yet.

Lint relaxations in tests
~~~~~~~~~~~~~~~~~~~~~~~~~

The following rules are **suppressed** for test files (``**/tests/**``) via per-file-
ignores in ``ruff.toml``:

- ``print()`` is allowed (``T201``).
- Broad ``assertRaises`` context managers are allowed (``B017``).
- ``global`` statements for test fixtures are allowed (``PLW0603``).
- Literal membership tests (``x in [1, 2, 3]``) prefer readability over performance
  (``PLR6201``).
- First-element access via ``list(x)[0]`` instead of ``next(iter(x))`` is allowed
  (``RUF015``).

Test naming
-----------

- Files: ``tests/test_<feature>.py``
- Classes: ``class TestFeatureName(TransactionCase):``
- Methods: ``def test_<specific_scenario>(self):``
- Use specific assertions (``assertEqual``, ``assertIn``, ``assertRaises``) rather than
  bare ``assertTrue``/``assertFalse``.

Test completeness
-----------------

**Negative tests are mandatory.** Every test class must include at least one test for an
expected failure path:

- For constraints: verify that invalid input raises ``ValidationError``.
- For access rules: verify that unauthorized users get ``AccessError``.
- For workflows: verify that invalid state transitions fail.

**Parameterized tests** — use ``subTest()`` to cover multiple inputs in a single method:

.. code-block:: python

   def test_tax_calculation(self):
       cases = [
           (100.0, 0.16, 16.0),
           (200.0, 0.08, 16.0),
           (0.0, 0.16, 0.0),
       ]
       for amount, rate, expected in cases:
           with self.subTest(amount=amount, rate=rate):
               result = self.env['account.tax']._compute_amount(amount, rate)
               self.assertAlmostEqual(result, expected, places=2)

Test structure
--------------

Use the **Arrange / Act / Assert** pattern. Separate sections with blank lines:

.. code-block:: python

   def test_order_confirmation_sets_date(self):
       # Arrange
       order = self.env['sale.order'].create({
           'partner_id': self.partner.id,
           'order_line': [Command.create({'product_id': self.product.id})],
       })

       # Act
       order.action_confirm()

       # Assert
       self.assertEqual(order.state, 'sale')
       self.assertTrue(order.date_order)

Tagging
-------

- Default: ``standard`` + ``at_install``.
- For ``HttpCase``: ``@tagged('post_install', '-at_install')``.
- For slow or integration tests: ``@tagged('-standard', 'heavy')``.


Migration Scripts
=================

Directory structure
-------------------

::

   migrations/
     19.0.1.1.0/
       pre-migrate.py
       post-migrate.py

The version in the directory name must match the ``version`` in ``__manifest__.py``
that introduces the breaking change.

Lint rules are **relaxed** for migration scripts (``**/migrations/**``) — ``E501``
(line length), ``UP`` (pyupgrade), ``PTH`` (pathlib), and ``ERA`` (commented-out code)
are all suppressed because migration scripts use raw SQL, legacy patterns, and
commented-out reference code.

Script types
------------

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Script
     - ORM Available
     - Use Case
   * - ``pre-migrate.py``
     - No (SQL only)
     - Rename columns, prevent data loss before the ORM recreates them.
   * - ``post-migrate.py``
     - Yes
     - Data transformation, field value migration using the ORM.
   * - ``end-migrate.py``
     - Yes
     - Cross-module cleanup after all modules are processed.

Standard signature:

.. code-block:: python

   def migrate(cr, version):
       if not version:
           return
       # migration logic

**When required:** adding/removing required fields on existing models, changing field
types, renaming models or fields, complex data transformations.

**Not required:** adding optional fields, new module installations, view-only changes,
adding/removing ``Many2many`` relationships.


Git
===

Commit message format
---------------------

Every commit message follows this structure::

   [TAG] module: short description

   Optional longer description explaining *why* this change was made,
   not *what* changed (the diff shows that).

   Task: 12345
   Fixes #678

The header should complete the sentence: *"If applied, this commit will..."*
Aim for ~50 characters in the header, 72 max.

Available tags
--------------

.. list-table::
   :header-rows: 1
   :widths: 15 85

   * - Tag
     - Meaning
   * - ``[FIX]``
     - Bug fix
   * - ``[IMP]``
     - Improvement / enhancement to existing feature
   * - ``[ADD]``
     - New module or feature
   * - ``[REM]``
     - Removal of code or resource
   * - ``[REF]``
     - Refactoring (no functional change)
   * - ``[MOV]``
     - File relocation (preserve history with ``git mv``)
   * - ``[REV]``
     - Revert a previous commit
   * - ``[REL]``
     - Release version
   * - ``[MERGE]``
     - Merge commit
   * - ``[I18N]``
     - Translation update
   * - ``[PERF]``
     - Performance optimization
   * - ``[CLN]``
     - Code cleanup (no functional change)
   * - ``[LINT]``
     - Linting / formatting fix

Examples::

   [FIX] sale: prevent duplicate confirmation on concurrent clicks
   [IMP] account: add batch payment export for Mexican banks
   [ADD] fleet_gps: new module for real-time vehicle tracking
   [REF] stock: simplify reservation logic using filtered()


Code Review Checklist
=====================

Verify in every review:

**Security:**

1. ``cr.execute`` uses ``%s`` parameters or ``SQL()`` wrapper — no f-strings/``%``/``.format()``
2. ``sudo()`` calls whitelist fields for user-submitted data
3. Related fields to sensitive models (``ir.attachment``, ``hr.payslip``) have access controls
4. Public methods (no underscore) are intentionally exposed as RPC endpoints
5. ``assert`` is not used for security validation — use ``if``/``raise``
6. Exception handlers never expose raw tracebacks or SQL to users
7. Error handling is fail-closed — partial operations use ``cr.savepoint()``
8. No hardcoded URLs, credentials, or service endpoints in Python code

**Correctness:**

9. ``search()`` and ``search_count()`` are called outside loops
10. Compute methods assign fields directly (no ``write()``)
11. CRUD overrides call ``super()``
12. ``@api.depends`` lists every sub-field accessed in the method body
13. ``fields.Monetary`` has a matching currency field on the same model
14. Error types match intent: ``UserError`` for business, ``ValidationError`` for constraints
15. ``.exists()`` is called when records may have been deleted
16. No mutable default arguments (``def f(vals=None)`` with sentinel pattern)
17. Method overrides use ``@typing.override`` decorator

**Performance:**

18. ``search_count()`` used for counts — not ``len(search())``
19. ``_read_group()`` used for aggregation — not Python-side ``sum()``/``len()``
20. Transactions are managed by the framework (no ``cr.commit()`` outside ``_commit_progress()``)
21. Cron jobs process in batches with ``split_every()`` and ``self.env['ir.cron']._commit_progress()``
22. Locking uses ``NOWAIT`` or ``SKIP LOCKED`` — no unbounded waits
23. Raw SQL in PR includes ``EXPLAIN ANALYZE`` output in description
24. State-filtered tables use partial indexes

**Testing:**

25. Every test class includes at least one negative test (expected failure path)
26. Tests never call ``cr.commit()``
27. Parameterized scenarios use ``subTest()``

**Style (human-reviewed — linter cannot catch these):**

28. External HTTP requests include a ``timeout`` parameter
29. Logging uses ``_logger`` with lazy ``%s`` formatting (not f-strings, not ``print()``)
30. ``_()`` receives literal strings with ``%s`` placeholders — no f-strings inside ``_()``
31. Company/user references use ``self.env.company`` / ``self.env.user``
32. Context keys use ``self.env.context.get()`` — not direct dict access
33. Methods stay under ~40 lines — extract sub-methods for longer logic
34. Comprehensions use at most one ``for`` and one ``if``

**Linter-enforced (verify ``ruff check`` passes):**

35. No ``print()`` or debugger statements in production code (``T10``/``T20``)
36. No commented-out code blocks (``ERA001``)
37. ``pathlib.Path`` used instead of ``os.path`` (``PTH``)
38. New exception re-raises use ``from`` chaining (``B904`` suppressed for legacy, expected in new code)
39. No ``datetime.utcnow()`` or ``datetime.utcfromtimestamp()`` — use ``datetime.now(UTC)`` (``DTZ003``/``DTZ004``)
40. ``ruff format`` has been run (consistent whitespace, double quotes, trailing commas)
41. External HTTP requests include a ``timeout`` parameter (``S113``)
42. No ``verify=False`` in ``requests``/``httpx`` calls (``S501``)
43. Regex patterns use raw strings ``r""`` — no unescaped backslashes (``RUF039``)
44. No float equality comparisons in financial code — use ``float_compare()`` (``RUF069``)


References
==========

- `Odoo 19.0 Coding Guidelines <https://www.odoo.com/documentation/19.0/contributing/development/coding_guidelines.html>`_
- `Odoo 19.0 Git Guidelines <https://www.odoo.com/documentation/19.0/contributing/development/git_guidelines.html>`_
- `PEP 8 — Style Guide for Python Code <https://peps.python.org/pep-0008/>`_
- `OCA Contributing Guidelines <https://github.com/OCA/odoo-community.org/blob/master/website/Contribution/CONTRIBUTING.rst>`_
- `OWASP Top 10 (2025) <https://owasp.org/Top10/>`_
- `Google Python Style Guide <https://google.github.io/styleguide/pyguide.html>`_
- ``core/ruff.toml`` for automated lint rules
