# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import AccessError


class L10nPhPosLineVoid(models.Model):
    _name = "l10n_ph.pos.line.void"
    _description = "POS Line Void Audit Log"
    _order = "logged_at desc, id desc"

    transaction_date = fields.Datetime(
        string="Transaction Date & Timestamp",
        help="Date and time when the transaction event happened in POS.",
        index=True,
    )
    logged_at = fields.Datetime(
        string="Log Date & Timestamp",
        help="Date and time when the audit entry was recorded in the backend.",
        default=fields.Datetime.now,
        index=True,
    )
    approver_badge_number = fields.Char(string="Approver Badge Number")
    approver_employee_id = fields.Many2one(
        "hr.employee",
        string="Approver",
        required=True,
        index=True,
    )
    cashier_badge_number = fields.Char(string="Cashier Badge Number")
    cashier_employee_id = fields.Many2one(
        "hr.employee",
        string="Cashier",
        index=True,
    )
    config_id = fields.Many2one(
        "pos.config",
        string="Point of Sale",
        required=True,
        index=True,
    )
    session_id = fields.Many2one(
        "pos.session",
        string="Session",
        required=True,
        index=True,
    )
    reason = fields.Text(string="Reason")
    remark = fields.Text(string="Remark")
    product_id = fields.Many2one(
        "product.product",
        string="Item / Product",
        required=True,
    )
    description = fields.Text(string="Description")
    quantity = fields.Float(string="Quantity", digits="Product Unit")
    unit_price = fields.Float(string="Unit Price", digits="Product Price")
    net_amount = fields.Monetary(
        string="Net Amount",
        currency_field="company_currency_id",
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        related="config_id.company_id",
        store=True,
        readonly=True,
        index=True,
    )
    company_currency_id = fields.Many2one(
        "res.currency",
        related="company_id.currency_id",
        string="Currency",
    )
    user_id = fields.Many2one("res.users", string="Logged By")
    source_uid = fields.Char(
        string="Source Action UID",
        index=True,
        copy=False,
        help="Stable identifier used to avoid duplicate audit entries during offline replay.",
    )

    def _check_immutability(self):
        """Enforce immutability of audit logs. Only superusers can modify."""
        if not self.env.is_superuser():
            raise AccessError(
                self.env._("Line void audit logs are immutable."),
            )

    @api.model_create_multi
    def create(self, vals_list):
        self._check_immutability()
        return super().create(vals_list)

    def write(self, vals):
        self._check_immutability()
        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_immutable(self):
        self._check_immutability()
