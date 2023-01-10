# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class Partner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'

    # NOT A REAL PROPERTY !!!!
    property_product_pricelist = fields.Many2one(
        'product.pricelist', 'Pricelist', compute='_compute_product_pricelist',
        inverse="_inverse_product_pricelist", company_dependent=False,
        domain=lambda self: [('company_id', 'in', (self.env.company.id, False))],
        help="This pricelist will be used, instead of the default one, for sales to the current partner")

    @api.depends('country_id')
    @api.depends_context('company')
    def _compute_product_pricelist(self):
        company = self.env.company.id
        res = self.env['product.pricelist']._get_partner_pricelist_multi(self.ids, company_id=company)
        for p in self:
            p.property_product_pricelist = res.get(p.id)

    def _inverse_product_pricelist(self):
        for partner in self:
            pls = self.env['product.pricelist'].search(
                [('country_group_ids.country_ids.code', '=', partner.country_id and partner.country_id.code or False)],
                limit=1
            )
            default_for_country = pls and pls[0]
            actual = self.env['ir.property']._get('property_product_pricelist', 'res.partner', 'res.partner,%s' % partner.id)
            # update at each change country, and so erase old pricelist
            if partner.property_product_pricelist or (actual and default_for_country and default_for_country.id != actual.id):
                # keep the company of the current user before sudo
                self.env['ir.property']._set_multi(
                    'property_product_pricelist',
                    partner._name,
                    {partner.id: partner.property_product_pricelist or default_for_country.id},
                    default_value=default_for_country.id
                )

    def _commercial_fields(self):
        return super(Partner, self)._commercial_fields() + ['property_product_pricelist']
