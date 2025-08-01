# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ProductPricelist(models.Model):
    _inherit = 'product.pricelist'

    partners_count = fields.Integer(compute='_compute_partners_count')
    partners_label = fields.Char(related='company_id.partnership_label')

    def _compute_partners_count(self):
        partners_data = self.env['res.partner']._read_group(
            domain=[('specific_property_product_pricelist', 'in', self.ids)],
            groupby=['specific_property_product_pricelist'],
            aggregates=['__count'],
        )
        mapped_data = {pricelist.id: count for pricelist, count in partners_data}
        for pricelist in self:
            pricelist.partners_count = mapped_data.get(pricelist.id, 0)

    @api.model
    def _get_partner_pricelist_multi(self, partner_ids):
        res = super()._get_partner_pricelist_multi(partner_ids)
        for partner in self.env['res.partner'].with_context(active_test=False).browse(partner_ids):
            if not res[partner.id] or (res[partner.id].name == "Default"):
                if pricelist := partner.commercial_partner_id.grade_id.default_pricelist_id:
                    res[partner.id] = pricelist
        return res
