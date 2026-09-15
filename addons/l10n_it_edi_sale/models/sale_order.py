from odoo import api, fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    l10n_it_origin_document_type = fields.Selection(
        selection=[
            ("purchase_order", "Purchase Order"),
            ("contract", "Contract"),
            ("agreement", "Agreement"),
        ],
        string="Origin Document Type",
        copy=False,
    )
    l10n_it_origin_document_name = fields.Char(
        string="Origin Document Name",
        copy=False,
    )
    l10n_it_origin_document_date = fields.Date(
        string="Origin Document Date",
        copy=False,
    )
    l10n_it_cig = fields.Char(
        string="CIG",
        copy=False,
        help="Tender Unique Identifier",
    )
    l10n_it_cup = fields.Char(
        string="CUP",
        copy=False,
        help="Public Investment Unique Identifier",
    )
    # Technical field for showing the above fields or not
    l10n_it_partner_pa = fields.Boolean(compute="_compute_l10n_it_partner_pa")

    @api.depends("partner_id.commercial_partner_id.l10n_it_pa_index", "company_id")
    def _compute_l10n_it_partner_pa(self):
        for order in self:
            partner = order.partner_id.commercial_partner_id
            order.l10n_it_partner_pa = partner and (
                partner._l10n_it_edi_is_public_administration()
                or len(partner.l10n_it_pa_index or "") == 7
            )

    def _prepare_invoice_vals(self):
        res = super()._prepare_invoice_vals()
        has_origin_document_fields_filled = any(
            [
                self.l10n_it_origin_document_type,
                self.l10n_it_origin_document_name,
                self.l10n_it_origin_document_date,
            ]
        )
        has_cup_or_cig_fields_filled = self.l10n_it_cig or self.l10n_it_cup
        # If at least one of the origin_document fields is filled, we do not fill missing values with the sale order
        # values to avoid having mismatched origin_document information (e.g. user-entered doc name but SO date)
        _debug.logic(
            "it_origin_document",
            order=self,
            by="explicit"
            if has_origin_document_fields_filled
            else ("from_order" if has_cup_or_cig_fields_filled else "none"),
        )
        if has_origin_document_fields_filled:
            res.update(
                {
                    "l10n_it_origin_document_type": self.l10n_it_origin_document_type,
                    "l10n_it_origin_document_name": self.l10n_it_origin_document_name,
                    "l10n_it_origin_document_date": self.l10n_it_origin_document_date,
                    "l10n_it_cig": self.l10n_it_cig,
                    "l10n_it_cup": self.l10n_it_cup,
                }
            )
        # Otherwise, if the CUP and/or CIG are filled but origin_document fields are not, pass SO values to invoice
        elif has_cup_or_cig_fields_filled:
            res.update(
                {
                    "l10n_it_origin_document_type": "purchase_order",
                    "l10n_it_origin_document_name": self.name,
                    "l10n_it_origin_document_date": self.date_order,
                    "l10n_it_cig": self.l10n_it_cig,
                    "l10n_it_cup": self.l10n_it_cup,
                }
            )
        return res
