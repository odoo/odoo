from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"
    _description = "Analytic Line"

    product_id = fields.Many2one(
        comodel_name="product.product",
        index="btree_not_null",
        check_company=True,
    )
    product_category = fields.Many2one(related="product_id.categ_id")
    general_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Financial Account",
        compute="_compute_general_account_id",
        store=True,
        readonly=False,
        ondelete="restrict",
        check_company=True,
    )
    journal_id = fields.Many2one(
        comodel_name="account.journal",
        related="move_line_id.journal_id",
        string="Financial Journal",
        readonly=True,
        check_company=True,
    )
    partner_id = fields.Many2one(
        compute="_compute_partner_id",
        store=True,
        readonly=False,
    )
    move_line_id = fields.Many2one(
        comodel_name="account.move.line",
        string="Journal Item",
        index=True,
        ondelete="cascade",
        check_company=True,
    )
    code = fields.Char(size=8)
    ref = fields.Char(string="Ref.")
    category = fields.Selection(
        selection_add=[("invoice", "Customer Invoice"), ("vendor_bill", "Vendor Bill")]
    )

    @api.constrains("move_line_id", "general_account_id")
    @_debug.perf.timed
    def _check_general_account_id(self):
        for line in self:
            if (
                line.move_line_id
                and line.general_account_id != line.move_line_id.account_id
            ):
                raise ValidationError(
                    _("The journal item is not linked to the correct financial account")
                )

    @api.model_create_multi
    @_debug.perf.timed
    def create(self, vals_list):
        if _debug.lifecycle.enabled:
            _debug.lifecycle(
                "create",
                model=self._name,
                count=len(vals_list),
                fields=sorted({key for vals in vals_list for key in vals}),
            )
        analytic_lines = super().create(vals_list)
        analytic_lines.move_line_id._update_analytic_distribution()
        return analytic_lines

    @_debug.perf.timed
    def write(self, vals):
        _debug.lifecycle("write", records=self, fields=sorted(vals))
        affected_move_lines = self.move_line_id
        res = super().write(vals)
        if any(
            field in vals
            for field in ["amount", "move_line_id"] + self._get_plan_fnames()
        ):
            if "move_line_id" in vals:
                affected_move_lines |= self.move_line_id
            affected_move_lines._update_analytic_distribution()
        return res

    @_debug.perf.timed
    def unlink(self):
        _debug.lifecycle("unlink", unlink=self)
        affected_move_lines = self.move_line_id
        res = super().unlink()
        affected_move_lines._update_analytic_distribution()
        return res

    @api.depends("move_line_id")
    def _compute_general_account_id(self):
        for line in self:
            line.general_account_id = line.move_line_id.account_id

    @api.depends("move_line_id.partner_id")
    def _compute_partner_id(self):
        for line in self:
            line.partner_id = line.move_line_id.partner_id or line.partner_id

    @api.onchange("product_id", "product_uom_id", "unit_amount", "currency_id")
    def on_change_unit_amount(self):
        if not self.product_id:
            _debug.logic("unit_amount_skipped", line=self, reason="no_product")
            return {}

        prod_accounts = self.product_id.product_tmpl_id.with_company(
            self.company_id
        )._get_product_accounts()
        unit = self.product_uom_id
        account = prod_accounts["expense"]
        _debug.logic("uom_resolved", line=self, fallback=not unit, account=account)
        if not unit:
            unit = self.product_id.uom_id

        amount_unit = self.product_id._get_prices("standard_price", uom=unit)[
            self.product_id.id
        ]
        amount = amount_unit * self.unit_amount or 0.0
        result = (
            self.currency_id.round(amount) if self.currency_id else round(amount, 2)
        ) * -1
        self.amount = result
        self.general_account_id = account
        self.product_uom_id = unit
        return None

    @api.model
    def view_header_get(self, view_id, view_type):
        if self.env.context.get("account_id"):
            return _(
                "Entries: %(account)s",
                account=self.env["account.analytic.account"]
                .browse(self.env.context["account_id"])
                .name,
            )
        return super().view_header_get(view_id, view_type)
