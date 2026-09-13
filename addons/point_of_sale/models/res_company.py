from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Domain

from ..tools import debug_log as dbg


class ResCompany(models.Model):
    _name = "res.company"
    _inherit = ["res.company", "mixin.pos.load"]

    point_of_sale_update_stock_quantities = fields.Selection(
        selection=[
            ("closing", "At the session closing"),
            ("real", "In real time"),
        ],
        string="Update quantities in stock",
        default="real",
        help="At the session closing: A picking is created for the entire session when it's closed\n In real time: Each order sent to the server create its own picking",
    )
    point_of_sale_use_ticket_qr_code = fields.Boolean(
        string="Self-service invoicing",
        default=True,
        help="Print information on the receipt to allow the customer to easily access the invoice anytime, from Odoo's portal.",
    )
    point_of_sale_ticket_unique_code = fields.Boolean(
        string="Generate a code on ticket",
        help="Add a 5-digit code on the receipt to allow the user to request the invoice for an order on the portal.",
    )
    point_of_sale_ticket_portal_url_display_mode = fields.Selection(
        selection=[
            ("qr_code", "QR code"),
            ("url", "URL"),
            ("qr_code_and_url", "QR code + URL"),
        ],
        string="Print",
        default="qr_code_and_url",
        required=True,
        help="Choose how the URL to the portal will be print on the receipt.",
    )

    @api.model
    def _load_pos_data_domain(self, data, config):
        return [("id", "=", config.company_id.id)]

    @api.model
    def _load_pos_data_fields(self, config):
        return [
            "id",
            "currency_id",
            "email",
            "website",
            "company_registry",
            "vat",
            "name",
            "phone_ids",
            "partner_id",
            "country_id",
            "state_id",
            "tax_calculation_rounding_method",
            "nomenclature_id",
            "point_of_sale_use_ticket_qr_code",
            "point_of_sale_ticket_unique_code",
            "point_of_sale_ticket_portal_url_display_mode",
            "street",
            "city",
            "zip",
            "account_fiscal_country_id",
        ]

    @api.constrains(
        "fiscalyear_lock_date", "tax_lock_date", "sale_lock_date", "hard_lock_date"
    )
    def check_lock_dates(self):
        pos_session_model = self.env["pos.session"].sudo()
        for record in self:
            record = record.with_context(ignore_exceptions=True)
            fiscal_lock_date = max(
                record.user_fiscalyear_lock_date, record.user_hard_lock_date
            )
            sessions_in_period = pos_session_model.search(
                Domain("company_id", "child_of", record.id)
                & Domain("state", "!=", "closed")
                & Domain.OR(
                    (
                        Domain("start_at", "<=", fiscal_lock_date),
                        Domain("start_at", "<=", record.user_tax_lock_date),
                        Domain("config_id.journal_id.type", "=", "sale")
                        & Domain("start_at", "<=", record.user_sale_lock_date),
                    )
                )
            )
            if sessions_in_period:
                dbg.logic.debug(
                    "lock date on company %s refused by open sessions %s",
                    record.id,
                    dbg.rec(sessions_in_period),
                )
                sessions_str = ", ".join(sessions_in_period.mapped("name"))
                raise ValidationError(
                    _(
                        "Please close all the point of sale sessions in this period before closing it. Open sessions are: %s ",
                        sessions_str,
                    )
                )
