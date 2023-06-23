# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class Ewaybill(models.Model):
    _inherit = "l10n.in.ewaybill"

    def _compute_document_partners_details(self):
        super()._compute_document_partners_details()
        for ewaybill in self:
            purchase_id = ewaybill.stock_picking_id.purchase_id
            if purchase_id:
                if ewaybill.picking_type_code == 'outgoing':
                    ewaybill.partner_bill_from_id = purchase_id.company_id.partner_id
                elif ewaybill.picking_type_code != 'dropship':
                    ewaybill.partner_bill_from_id = purchase_id.partner_id
