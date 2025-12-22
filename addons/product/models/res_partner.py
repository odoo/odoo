# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # when the specific_property_product_pricelist is not defined
    # the fallback value may be computed with 2 ir.config_parameter
    # in self.env['product.pricelist']._get_partner_pricelist_multi
    # 1. res.partner.property_product_pricelist_{company_id}  # fallback for current company
    # 2. res.partner.property_product_pricelist               # fallback for all companies
    property_product_pricelist = fields.Many2one(
        comodel_name='product.pricelist',
        string="Pricelist",
        compute='_compute_product_pricelist',
        inverse="_inverse_product_pricelist",
        company_dependent=False,  # behave like company dependent field but is not company_dependent
        domain=lambda self: [('company_id', 'in', (self.env.company.id, False))],
        help="This pricelist will be used, instead of the default one, for sales to the current partner")

    # the specific pricelist to compute property_product_pricelist
    # this company dependent field shouldn't have any fallback in ir.default
    specific_property_product_pricelist = fields.Many2one(
        comodel_name='product.pricelist',
        company_dependent=True,
    )

    @api.depends('country_id', 'specific_property_product_pricelist')
    @api.depends_context('company', 'country_code')
    def _compute_product_pricelist(self):
        res = self.env['product.pricelist']._get_partner_pricelist_multi(self._ids)
        for partner in self:
            partner.property_product_pricelist = res.get(partner.id)

    def _inverse_product_pricelist(self):
        for partner in self:
            pls = self.env['product.pricelist'].search(
                [('country_group_ids.country_ids.code', '=', partner.country_id and partner.country_id.code or False)],
                limit=1
            )
            default_for_country = pls
            actual = partner.specific_property_product_pricelist
            # update at each change country, and so erase old pricelist
            if partner.property_product_pricelist or (actual and default_for_country and default_for_country.id != actual.id):
                partner.specific_property_product_pricelist = False if partner.property_product_pricelist.id == default_for_country.id else partner.property_product_pricelist.id

    def _commercial_fields(self):
        return [
            *super()._commercial_fields(),
            'specific_property_product_pricelist',
        ]
