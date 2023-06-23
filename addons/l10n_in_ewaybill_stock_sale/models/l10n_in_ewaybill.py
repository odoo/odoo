# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class Ewaybill(models.Model):
    _inherit = "l10n.in.ewaybill"

    def _compute_document_partners_details(self):
        super()._compute_document_partners_details()
        for ewaybill in self:
            sale_id = ewaybill.stock_picking_id.sale_id
            if sale_id:
                if ewaybill.picking_type_code == 'incoming':
                    ewaybill.partner_bill_to_id = sale_id.company_id.partner_id
                else:
                    ewaybill.partner_bill_to_id = sale_id.partner_invoice_id
