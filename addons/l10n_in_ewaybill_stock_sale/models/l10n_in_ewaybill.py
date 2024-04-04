# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class Ewaybill(models.Model):
    _inherit = "l10n.in.ewaybill"

    def _compute_document_partners_details(self):
        super()._compute_document_partners_details()
        for ewaybill in self:
            if sale_id := ewaybill.picking_id.sale_id:
                ewaybill.partner_bill_to_id = (
                    ewaybill.picking_type_code == 'incoming' and
                    sale_id.company_id.partner_id or sale_id.partner_invoice_id
                )
