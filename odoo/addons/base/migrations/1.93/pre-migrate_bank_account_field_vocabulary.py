r"""Pre-migration: one vocabulary for the fields that hold a bank account.

`res.partner.bank` became `res.partner.bank.account` in base 1.89. The fields
pointing at it kept names derived from the OLD model name -- `partner_bank_id`
reads "the partner-bank", which is the same mistake the model name carried --
and the workspace had three spellings for one comodel.

    partner_bank_id            -> bank_account_id
    available_partner_bank_ids -> available_bank_account_ids
    payment_partner_bank_id    -> payment_bank_account_id
    untrusted_bank_ids         -> untrusted_bank_account_ids
    res_partner_bank_id        -> bank_account_id
    main_bank_id               -> main_bank_account_id
    l10n_hk_autopay_partner_bank_id -> l10n_hk_autopay_bank_account_id
    bank_id                    -> bank_account_id   (l10n_id.qris.transaction ONLY)

WHY THIS IS ONE MIGRATION IN `base` AND NOT NINE PER MODULE. The convention here
is that a module migrates its own fields, and this deliberately departs from it.
`partner_bank_id` spans nine modules, and the expression rewrite --
`rename_in_stored_expressions` over views, domains, contexts, filters, record
rules and server-action code -- is global by nature. Split per module, the first
module to upgrade rewrites every stored expression in the database to the new
name while the other eight still declare the old one, and every view they own
breaks until they catch up. base migrates before all of them, so doing it once
here is the only ordering with no broken intermediate state.

`bank_id` IS THE ONE THAT MUST NOT BE SWEPT. Every other name here is unique to
this comodel across the whole registry, which is what makes `unique=True` sound
for them. `bank_id` is not: measured on a 148-module database, ZERO fields named
`bank_id` point at a bank account and THREE point at `res.bank`. The only
bank-account one is `l10n_id.qris.transaction`'s, so it is renamed by model and
its expressions are rewritten scoped to that model. A `unique=True` rewrite
would have renamed three `res.bank` pointers.

NOT RENAMED, and the block is worth recording: `res.partner.bank_ids` stays.
`bank_ids -> bank_account_ids` is a name clash by construction, not a judgement
call -- `hr.employee` declares its own `bank_account_ids` (the payroll-selected
subset, `domain="[('partner_id', '=', partner_id), ...]"`) and `res.users`
re-exports it as a related field, while both also see `res.partner.bank_ids`
through `_inherits`. Renaming the parent's would put two fields of one name on
the child. Four models delegate `res.partner` -- `res.company` and `res.bank` do
not declare the name and would not collide -- so it is two sites with one cause,
both from `hr`, and it needs an `hr` decision rather than a rename.

Every `rename_field` here is a no-op on a database where the module owning the
model is not installed: it finds no `ir.model.fields` row and returns.
"""

import logging

from odoo.libs.sql import SQL
from odoo.tools.module_data import rename_field, rename_in_stored_expressions

_logger = logging.getLogger(__name__)

# (old, new, models). The model list is what `ir_model_fields` reports at
# relation = 'res.partner.bank.account', plus the declarations an AST scan of the
# four repositories finds in modules that database did not install.
RENAMES = (
    (
        "partner_bank_id",
        "bank_account_id",
        (
            "account.bank.statement.line",
            "account.move",
            "account.payment",
            "account.payment.register",
            "account.return.payment.wizard",
            "bacs.ddi",
            "hr.expense.stripe.topup.wizard",
            "l10n_es_reports.aeat.boe.mod111and115and303.export.wizard",
            "l10n_pl.bank.account.verification",
            "qr.code.payment.wizard",
            "sdd.mandate",
        ),
    ),
    (
        "available_partner_bank_ids",
        "available_bank_account_ids",
        ("account.payment", "account.payment.register"),
    ),
    ("payment_partner_bank_id", "payment_bank_account_id", ("account.return.type",)),
    (
        "l10n_hk_autopay_partner_bank_id",
        "l10n_hk_autopay_bank_account_id",
        ("res.company", "res.config.settings"),
    ),
    ("untrusted_bank_ids", "untrusted_bank_account_ids", ("account.payment.register",)),
    (
        "res_partner_bank_id",
        "bank_account_id",
        ("account.setup.bank.manual.config",),
    ),
    (
        "main_bank_id",
        "main_bank_account_id",
        ("hr.employee", "res.bank", "res.company", "res.partner", "res.users"),
    ),
)

# Scoped, never global -- see the module docstring.
SCOPED_RENAMES = (("bank_id", "bank_account_id", "l10n_id.qris.transaction"),)


def _rewrite_qweb_arches(cr, old, new):
    r"""Rewrite the occurrences `rename_in_view_arches` cannot reach.

    That helper resolves an xpath by walking `@name='...'` predicates, which is
    the form form and list inheritance uses. A QWeb report template inherits by
    whatever identifies the node -- here

        <xpath expr="//p[@name='payment_communication']//t[@t-if='o.partner_bank_id']">

    anchors on `@t-if`, so `_XPATH_NAME` never sees the field and the expression
    is left with the old name while the PARENT view it points into is rewritten.
    The xpath then locates nothing and the registry fails to load. Measured: it
    missed exactly one view of the 21 carrying the name.

    A whole-arch rewrite is sound HERE only because every name in RENAMES was
    verified unique to this comodel across the registry -- no other model has a
    field so called, so there is no namesake to damage. That is the precondition
    the helper cannot assume and this migration can.
    """
    pattern = rf"\y{old}\y"
    cr.execute(
        SQL(
            "UPDATE ir_ui_view SET arch_db = regexp_replace(arch_db::text, %s, %s, 'g')::jsonb "
            "WHERE arch_db::text ~ %s",
            pattern,
            new,
            pattern,
        )
    )
    return cr.rowcount


def _rewrite_default_context_keys(cr, old, new):
    r"""`default_<field>` is a context key, and `\y` does not see inside it.

    PostgreSQL's word boundary treats `_` as a word character, so a rewrite of
    `partner_bank_id` passes straight over `default_partner_bank_id` -- measured
    directly. The ORM reads that key to seed a default, so leaving it behind does
    not raise anything: the default simply stops applying.
    """
    rewritten = 0
    for table, column in (
        ("ir_ui_view", "arch_db"),
        ("ir_act_window", "context"),
        ("ir_filters", "context"),
    ):
        cr.execute(
            SQL(
                "UPDATE %s SET %s = replace(%s::text, %s, %s)::%s WHERE %s::text LIKE %s",
                SQL.identifier(table),
                SQL.identifier(column),
                SQL.identifier(column),
                f"default_{old}",
                f"default_{new}",
                SQL("jsonb") if column == "arch_db" else SQL("text"),
                SQL.identifier(column),
                f"%default_{old}%",
            )
        )
        rewritten += cr.rowcount
    return rewritten


def migrate(cr, version):
    if not version:
        return

    for old, new, models in RENAMES:
        for model in models:
            rename_field(cr, model, old, new)
        rewritten = rename_in_stored_expressions(cr, old, new, unique=True)
        arches = _rewrite_qweb_arches(cr, old, new)
        defaults = _rewrite_default_context_keys(cr, old, new)
        _logger.info(
            "%s -> %s on %d model(s), %d expression(s), %d qweb arch(es), "
            "%d default-key row(s)",
            old,
            new,
            len(models),
            rewritten,
            arches,
            defaults,
        )

    for old, new, model in SCOPED_RENAMES:
        rename_field(cr, model, old, new)
        rewritten = rename_in_stored_expressions(cr, old, new, model=model)
        _logger.info(
            "%s -> %s on %s only, %d stored expression(s) rewritten",
            old,
            new,
            model,
            rewritten,
        )
