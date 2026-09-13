from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.libs.debug_log import DebugLog
from odoo.tools import float_round

_debug = DebugLog(__name__)


class AccountCashRounding(models.Model):
    _name = "account.cash.rounding"
    _description = "Account Cash Rounding"
    _check_company_auto = True

    name = fields.Char(string="Name", translate=True, required=True)
    rounding = fields.Float(
        string="Rounding Precision",
        required=True,
        default=0.01,
        help="Represent the non-zero value smallest coinage (for example, 0.05).",
    )
    strategy = fields.Selection(
        [
            ("biggest_tax", "Modify tax amount"),
            ("add_invoice_line", "Add a rounding line"),
        ],
        string="Rounding Strategy",
        default="add_invoice_line",
        required=True,
        help="Specify which way will be used to round the invoice amount to the rounding precision",
    )
    profit_account_id = fields.Many2one(
        "account.account",
        string="Profit Account",
        company_dependent=True,
        check_company=True,
        domain="[('account_type', 'not in', ('asset_receivable', 'liability_payable'))]",
        ondelete="restrict",
    )
    loss_account_id = fields.Many2one(
        "account.account",
        string="Loss Account",
        company_dependent=True,
        check_company=True,
        domain="[('account_type', 'not in', ('asset_receivable', 'liability_payable'))]",
        ondelete="restrict",
    )
    rounding_method = fields.Selection(
        string="Rounding Method",
        required=True,
        selection=[("UP", "Up"), ("DOWN", "Down"), ("HALF-UP", "Nearest")],
        default="HALF-UP",
        help="The tie-breaking rule used for float rounding operations",
    )

    @api.constrains("rounding")
    @_debug.perf.timed
    def _check_rounding(self):
        for record in self:
            if record.rounding <= 0:
                raise ValidationError(
                    _("Please set a strictly positive rounding value.")
                )

    def round(self, amount):
        return float_round(
            amount,
            precision_rounding=self.rounding,
            rounding_method=self.rounding_method,
        )

    def compute_difference(self, currency, amount):
        amount = currency.round(amount)
        difference = self.round(amount) - amount
        return currency.round(difference)
