# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _


class ResCompany(models.Model):
    _inherit = "res.company"

    @api.model_create_multi
    def create(self, vals_list):
        companies = super(ResCompany, self).create(vals_list)
        ProductPricelist = self.env['product.pricelist']
        for new_company in companies:
            pricelist = ProductPricelist.search([
                ('currency_id', '=', new_company.currency_id.id),
                ('company_id', '=', False)
            ], limit=1)
            if not pricelist:
                params = {'currency': new_company.currency_id.name}
                pricelist = ProductPricelist.create({
                    'name': _("Default %(currency)s pricelist") %  params,
                    'currency_id': new_company.currency_id.id,
                })
            self.env['ir.property']._set_default(
                'property_product_pricelist',
                'res.partner',
                pricelist,
                new_company,
            )
        return companies

    def write(self, values):
        # When we modify the currency of the company, we reflect the change on the list0 pricelist, if
        # that pricelist is not used by another company. Otherwise, we create a new pricelist for the
        # given currency.
        ProductPricelist = self.env['product.pricelist']
        currency_id = values.get('currency_id')
        main_pricelist = self.env.ref('product.list0', False)
        if currency_id and main_pricelist:
            nb_companies = self.search_count([])
            for company in self:
                existing_pricelist = ProductPricelist.search(
                    [('company_id', 'in', (False, company.id)),
                     ('currency_id', 'in', (currency_id, company.currency_id.id))])
                if existing_pricelist and any(currency_id == x.currency_id.id for x in existing_pricelist):
                    continue
                if currency_id == company.currency_id.id:
                    continue
                currency_match = main_pricelist.currency_id == company.currency_id
                company_match = (main_pricelist.company_id == company or
                                 (main_pricelist.company_id.id is False and nb_companies == 1))
                if currency_match and company_match:
                    main_pricelist.write({'currency_id': currency_id})
                else:
                    params = {'currency': self.env['res.currency'].browse(currency_id).name}
                    pricelist = ProductPricelist.create({
                        'name': _("Default %(currency)s pricelist") %  params,
                        'currency_id': currency_id,
                    })
                    self.env['ir.property']._set_default(
                        'property_product_pricelist',
                        'res.partner',
                        pricelist,
                        company,
                    )
        return super(ResCompany, self).write(values)
