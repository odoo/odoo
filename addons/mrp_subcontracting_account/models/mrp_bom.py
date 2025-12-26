# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    def _compute_bom_cost(self, product, boms_to_recompute=False):
        """ Add the price of the subcontracting supplier if it exists with the bom configuration.
        """
        price = super()._compute_bom_cost(product, boms_to_recompute)
        if self.type == 'subcontract':
            company = self.company_id or self.env.company
            seller = (
                product.with_company(company)._select_seller(quantity=self.product_qty, uom_id=self.uom_id, params={'subcontractor_ids': self.subcontractor_ids})
                if product
                else self.product_tmpl_id.seller_ids.filtered(lambda s: s.partner_id in self.subcontractor_ids and not s.company_id or s.company_id == company)[:1]
            )
            if seller:
                seller_price = seller.currency_id._convert(seller.price, company.currency_id, company, fields.Date.today())
                price += seller.uom_id._compute_price(seller_price, self.product_tmpl_id.uom_id)
        return price
