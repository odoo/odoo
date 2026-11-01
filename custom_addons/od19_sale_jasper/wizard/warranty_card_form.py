# -*- coding: utf-8 -*-
"""Warranty Card Form (ใบรับประกัน) - Jasper port re-targeted to Odoo 19.

The legacy template queried ``dtr_warranty_card`` / ``dtr_warranty_card_line``,
tables that do not exist in Odoo 19.  The port reads
:class:`od19.warranty.claim` (module ``od19_service_warranty``) instead, which
exposes the same information: claim number, product, lot/serial, install date
and warranty expiry (computed from the product warranty policy).
"""
from odoo import _, fields, models
from odoo.exceptions import UserError

from odoo.addons.od19_reporting_jasper.wizard.invoice_form import DATE_FORMATS


class WarrantyCardForm(models.TransientModel):
    _name = "warranty.card.form"
    _description = "Warranty Card Form"
    _inherit = "od19.jasper.report"

    name = fields.Char(default="Warranty Card")
    jasper_file = fields.Char(default=lambda self: self.get_jasper_file(__file__))
    p_language = fields.Selection(
        [("thai", "Thai"), ("english", "English")],
        string="Language",
        default="thai",
        required=True,
    )
    date_type = fields.Selection(
        [("AD", "AD"), ("BE", "BE")],
        string="Date Type",
        default="AD",
        required=True,
        help="AD = คริสตศักราช\nBE = พุทธศักราช",
    )
    date_format = fields.Selection(
        [(value, value) for value in DATE_FORMATS],
        string="Date Format",
        default="dd-MM-yyyy",
        required=True,
    )

    def _legacy_active_ids(self):
        ids = self.env.context.get("active_ids") or []
        if not ids:
            raise UserError(_("No document selected."))
        return ids

    def get_partner_ids_for_send_by_email(self):
        claims = self.env["od19.warranty.claim"].browse(
            self.env.context.get("active_ids", [])
        )
        return claims.mapped("partner_id")

    def get_parameters(self):
        ids = self._legacy_active_ids()
        self.name = self.get_file_name(ids, "od19.warranty.claim", "Warranty Card")
        return dict(
            self.get_common_parameters(),
            p_Where=" where claim.id in (%s) " % ", ".join(str(i) for i in ids),
        )
