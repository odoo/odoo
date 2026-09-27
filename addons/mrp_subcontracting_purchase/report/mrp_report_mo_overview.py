# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ReportMrpReport_Mo_Overview(models.AbstractModel):
    _inherit = 'report.mrp.report_mo_overview'

    def _get_subcontracted_bom(self, product_id, company_id, partner_id):
        return self.env['mrp.bom'].sudo()._bom_subcontract_find(
            product_id,
            company_id=company_id,
            subcontractor=partner_id,
        )

    def _calculate_po_price(self, po_line, quantity):
        price = super()._calculate_po_price(po_line, quantity)

        # for subcontracted products, take into account the BoM component cost
        bom = self._get_subcontracted_bom(po_line.product_id, po_line.company_id.id, po_line.order_id.partner_id)
        if bom:
            price += po_line.product_id._get_bom_components_price(bom) * quantity

        return price

    def _get_seller_resupply_data(self, product, quantity, rules_delay, uom_id, seller_info):
        seller_resupply_data = super()._get_seller_resupply_data(product, quantity, rules_delay, uom_id, seller_info)

        # for subcontracted products, take into account the BoM component cost
        bom = self._get_subcontracted_bom(product, seller_info['supplierinfo'].company_id.id, seller_info['partner_id'])
        if bom:
            seller_resupply_data['cost'] += product._get_bom_components_price(bom) * uom_id._compute_quantity(quantity, seller_info['uom_id'])

        return seller_resupply_data
