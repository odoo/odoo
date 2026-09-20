from datetime import UTC, datetime, time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from dateutil.relativedelta import relativedelta

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class MrpAccountWipAccountingLine(models.TransientModel):
    _name = "mrp.account.wip.accounting.line"
    _description = "Account move line to be created when posting WIP account move"

    account_id = fields.Many2one(comodel_name="account.account")
    label = fields.Char()
    debit = fields.Monetary(
        compute="_compute_debit",
        store=True,
        readonly=False,
    )
    credit = fields.Monetary(
        compute="_compute_credit",
        store=True,
        readonly=False,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        default=lambda self: self.env.company.currency_id,
    )
    wip_accounting_id = fields.Many2one(
        comodel_name="mrp.account.wip.accounting",
        string="WIP accounting wizard",
    )

    _check_debit_credit = models.Constraint(
        "CHECK ( debit = 0 OR credit = 0 )",
        "A single line cannot be both credit and debit.",
    )

    @api.depends("credit")
    def _compute_debit(self):
        for record in self:
            if not record.currency_id.is_zero(record.credit):
                record.debit = 0

    @api.depends("debit")
    def _compute_credit(self):
        for record in self:
            if not record.currency_id.is_zero(record.debit):
                record.credit = 0


class MrpAccountWipAccounting(models.TransientModel):
    _name = "mrp.account.wip.accounting"
    _description = "Wizard to post Manufacturing WIP account move"

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        productions = self.env["mrp.production"].browse(
            self.env.context.get("active_ids")
        )
        productions = productions.filtered(
            lambda mo: mo.state in ["progress", "to_close", "confirmed"]
        )
        if "journal_id" in fields_list:
            journal = self._get_company_or_category_default(
                "account_stock_journal_id", "property_stock_journal"
            )
            if journal:
                res["journal_id"] = journal.id
        if "reference" in fields_list:
            res["reference"] = _(
                "Manufacturing WIP - %(orders_list)s",
                orders_list=productions.mapped("name") or _("Manual Entry"),
            )
        if "mo_ids" in fields_list:
            res["mo_ids"] = [Command.set(productions.ids)]
        return res

    date = fields.Date(default=fields.Date.context_today)
    reversal_date = fields.Date(
        compute="_compute_reversal_date",
        precompute=True,
        store=True,
        readonly=False,
        required=True,
    )
    journal_id = fields.Many2one(
        comodel_name="account.journal",
        required=True,
    )
    reference = fields.Char()
    line_ids = fields.One2many(
        comodel_name="mrp.account.wip.accounting.line",
        inverse_name="wip_accounting_id",
        string="WIP accounting lines",
        compute="_compute_line_ids",
        store=True,
        readonly=False,
    )
    mo_ids = fields.Many2many(comodel_name="mrp.production")

    def _get_company_or_category_default(self, company_field, category_field):
        # The company carries the fact; the categories' default mirrors it and
        # stands in where a company has none.
        ProductCategory = self.env["product.category"]
        return self.env.company[company_field] or ProductCategory._fields[
            category_field
        ].get_company_dependent_fallback(ProductCategory)

    def _get_overhead_account(self):
        return self._get_company_or_category_default(
            "account_production_wip_overhead_account_id",
            "property_stock_account_production_cost_id",
        ).id

    def _get_day_end_utc(self, day):
        try:
            tz = ZoneInfo(self.env.context.get("tz") or self.env.user.tz or "UTC")
        except ZoneInfoNotFoundError, ValueError:
            tz = UTC
        return (
            datetime.combine(day, time.max, tzinfo=tz)
            .astimezone(UTC)
            .replace(tzinfo=None)
        )

    def _prepare_wip_line_vals(self, productions=False, date=False):
        if not productions:
            productions = self.env["mrp.production"]
        if not date:
            date = self._get_day_end_utc(fields.Date.context_today(self))
        compo_value = sum(
            ml.quantity_product_uom
            * (
                (ml.product_id.lot_valuated and ml.lot_id and ml.lot_id.standard_price)
                or ml.product_id.standard_price
            )
            for ml in productions.move_raw_ids.move_line_ids.filtered(
                lambda ml: ml.picked and ml.quantity and ml.date <= date
            )
        )
        overhead_value = productions.workorder_ids._get_cost(date)
        _debug.logic(
            "wip_line_values",
            productions=productions,
            components=compo_value,
            overhead=overhead_value,
        )
        sval_acc = self._get_company_or_category_default(
            "account_stock_valuation_id", "property_stock_valuation_account_id"
        ).id
        return [
            Command.create(
                {
                    "label": _("WIP - Component Value"),
                    "credit": compo_value,
                    "account_id": sval_acc,
                }
            ),
            Command.create(
                {
                    "label": _("WIP - Overhead"),
                    "credit": overhead_value,
                    "account_id": self._get_overhead_account(),
                }
            ),
            Command.create(
                {
                    "label": _(
                        "Manufacturing WIP - %(orders_list)s",
                        orders_list=productions.mapped("name") or _("Manual Entry"),
                    ),
                    "debit": compo_value + overhead_value,
                    "account_id": self.env.company.account_production_wip_account_id.id,
                }
            ),
        ]

    @api.depends("date")
    def _compute_reversal_date(self):
        for wizard in self:
            if not wizard.reversal_date or wizard.reversal_date <= wizard.date:
                wizard.reversal_date = wizard.date + relativedelta(days=1)

    @api.depends("date")
    def _compute_line_ids(self):
        for wizard in self:
            if not wizard.line_ids or wizard.mo_ids:
                wizard.line_ids = [Command.clear()] + wizard._prepare_wip_line_vals(
                    wizard.mo_ids, wizard._get_day_end_utc(wizard.date)
                )

    def action_confirm(self):
        self.check_singleton()
        if len(self.mo_ids.company_id) > 1:
            _debug.logic("wip_refused", reason="multi_company", productions=self.mo_ids)
            raise UserError(
                _(
                    "Post one WIP entry per company: the selected orders belong "
                    "to %(companies)s.",
                    companies=self.mo_ids.company_id.mapped("display_name"),
                )
            )
        if unaccounted := self.line_ids.filtered(lambda line: not line.account_id):
            _debug.logic("wip_refused", reason="no_account", lines=len(unaccounted))
            raise UserError(
                _(
                    "No account is configured for: %(labels)s. Set the WIP accounts "
                    "on the company, or the production and stock valuation accounts "
                    "on the product category.",
                    labels=unaccounted.mapped("label"),
                )
            )
        if (
            self.env.company.currency_id.compare_amounts(
                sum(self.line_ids.mapped("credit")), sum(self.line_ids.mapped("debit"))
            )
            != 0
        ):
            _debug.logic("wip_refused", reason="unbalanced", lines=len(self.line_ids))
            raise UserError(
                _(
                    "Please make sure the total credit amount equals the total debit amount."
                )
            )
        if self.reversal_date <= self.date:
            _debug.logic("wip_refused", reason="reversal_before_posting")
            raise UserError(_("Reversal date must be after the posting date."))
        move = (
            self.env["account.move"]
            .sudo()
            .create(
                {
                    "journal_id": self.journal_id.id,
                    "wip_production_ids": self.mo_ids.ids,
                    "date": self.date,
                    "ref": self.reference,
                    "move_type": "entry",
                    "line_ids": [
                        Command.create(
                            {
                                "name": line.label,
                                "account_id": line.account_id.id,
                                "debit": line.debit,
                                "credit": line.credit,
                            }
                        )
                        for line in self.line_ids
                    ],
                }
            )
        )
        _debug.lifecycle(
            "wip_entry_posted",
            move=move.id,
            productions=self.mo_ids,
            lines=len(self.line_ids),
        )
        move._post()
        move._reverse_moves(
            default_values_list=[
                {
                    "ref": _("Reversal of: %s", self.reference),
                    "wip_production_ids": self.mo_ids.ids,
                    "date": self.reversal_date,
                }
            ]
        )._post()
