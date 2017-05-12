# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class ResCompany(models.Model):
    _inherit = "res.company"

    @api.model
    def create(self, vals):
        new_company = super(ResCompany, self).create(vals)
        ProductPricelist = self.env['product.pricelist']
        pricelist = ProductPricelist.search([('currency_id', '=', new_company.currency_id.id), ('company_id', '=', False)], limit=1)
        if not pricelist:
            pricelist = ProductPricelist.create({
                'name': new_company.name,
                'currency_id': new_company.currency_id.id,
            })
        field = self.env['ir.model.fields'].search([('model', '=', 'res.partner'), ('name', '=', 'property_product_pricelist')])
        product_property = self.env['ir.property'].create({
            'name': 'property_product_pricelist',
            'value_reference': 'product.pricelist,%s' % pricelist.id,
            'fields_id': field.id
        })
        # multi-company security rules prevents access
        product_property.sudo().write({'company_id': new_company.id})
        return new_company

    @api.multi
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
                if main_pricelist.company_id == company or (main_pricelist.company_id.id is False and nb_companies == 1):
                    main_pricelist.write({'currency_id': currency_id})
                else:
                    pricelist = ProductPricelist.create({
                        'name': company.name,
                        'currency_id': currency_id,
                    })
                    field = self.env['ir.model.fields'].search([('model', '=', 'res.partner'), ('name', '=', 'property_product_pricelist')])
                    self.env['ir.property'].create({
                        'name': 'property_product_pricelist',
                        'company_id': company.id,
                        'value_reference': 'product.pricelist,%s' % pricelist.id,
                        'fields_id': field.id
                    })
        return super(ResCompany, self).write(values)
