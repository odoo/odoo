# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class Ewaybill(models.Model):
    _inherit = "l10n.in.ewaybill"

    def _compute_document_partners_details(self):
        super()._compute_document_partners_details()
        for ewaybill in self:
            purchase_id = ewaybill.stock_picking_id.purchase_id
            if ewaybill.stock_picking_id.is_dropship:
                ewaybill.partner_ship_to_id = purchase_id.dest_address_id
                ewaybill.partner_ship_from_id = purchase_id.partner_id
