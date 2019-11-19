# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _


class ResCompany(models.Model):
    _inherit = "res.company"

    @api.model
    def create(self, vals):
        # When we create a company, we define the default pricelist that should
        # be used (and create it if needed).
        new_company = super(ResCompany, self).create(vals)
        new_company._get_and_set_company_pricelist(new_company.currency_id.id, True)
        return new_company

    def write(self, values):
        # When we modify the currency of the company, we find or create
        # a pricelist in the given currency and set it as the default pricelist
        # for the company.
        currency_id = values.get('currency_id')
        # VFE TODO do not change anything if currency_id = self.currency_id ?
        if currency_id:
            self._get_and_set_company_pricelist(currency_id, False)
        return super(ResCompany, self).write(values)

    def _get_and_set_company_pricelist(self, currency_id, new_company=False):
        """Find/Create and set the default pricelist for each company in self.

        :param int currency_id: id of new currency.
        :param bool new_company: whether self are new companies or not.
            When it is the case, no company-restricted pricelist can be found
            for given currency, and a shared pricelist is used/created.
        """
        ProductPricelist = self.env['product.pricelist']
        currency = self.env['res.currency'].browse(currency_id)
        multi_company_pricelist = ProductPricelist.search([
            ('company_id', '=', False),
            ('currency_id', '=', currency_id)
        ], limit=1)
        for company in self:
            company_pricelist = ProductPricelist.search([
                ('company_id', '=', company.id),
                ('currency_id', '=', currency_id)
            ], limit=1) if not new_company else self.env['product.pricelist']
            if not company_pricelist and not multi_company_pricelist:
                multi_company_pricelist = ProductPricelist.sudo().create({
                    'name': _("Default %s pricelist") % currency.name,
                    'currency_id': currency_id,
                })
            pricelist = company_pricelist or multi_company_pricelist
            company._set_company_default_pricelist(pricelist)

    def _set_company_default_pricelist(self, pricelist):
        """
        :param pricelist:
        :type pricelist: product.pricelist
        """
        self.ensure_one()
        pricelist.ensure_one()
        self.env['ir.property'].sudo().set_default(
            'property_product_pricelist',
            'res.partner',
            pricelist,
            self,
        )
