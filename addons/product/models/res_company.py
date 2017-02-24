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
        self.env['ir.property'].create({
            'name': 'property_product_pricelist',
            'company_id': new_company.id,
            'value_reference': 'product.pricelist,%s' % pricelist.id,
            'fields_id': field.id
        })
        return new_company

    @api.multi
    def write(self, values):
        # The pricelist and its company must have the same currency to avoid some valuation troubles.
        # When the currency_id changes, we ensure that the pricelist keeps the same currency as it's
        # related company. If no company is specified, the write is still done because we suppose the
        # currency is the same in a multicompany environment sharing the same pricelist.
        currency_id = values.get('currency_id')
        if currency_id:
            pricelist_ids = self.env['product.pricelist'].search([('company_id', 'in', [self.id, False])])
            if pricelist_ids:
                pricelist_ids.write({'currency_id': currency_id})
        return super(ResCompany, self).write(values)
