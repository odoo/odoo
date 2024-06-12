# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ResCountry(models.Model):
    _inherit = 'res.country'

    def get_website_sale_countries(self, mode='billing'):
        res = self.sudo().search([])
        if mode == 'shipping':
            countries = self.env['res.country']

            delivery_carriers = self.env['delivery.carrier'].sudo().search([('website_published', '=', True)])
            for carrier in delivery_carriers:
                if not carrier.country_ids and not carrier.state_ids:
                    countries = res
                    break
                countries |= carrier.country_ids

            res = res & countries
        return res

    def get_website_sale_states(self, mode='billing'):
        res = self.sudo().state_ids
        if mode == 'shipping':
            states = self.env['res.country.state']
            dom = ['|', ('country_ids', 'in', self.id), ('country_ids', '=', False), ('website_published', '=', True)]
            delivery_carriers = self.env['delivery.carrier'].sudo().search(dom)

            for carrier in delivery_carriers:
                if not carrier.country_ids or not carrier.state_ids:
                    states = res
                    break
                states |= carrier.state_ids
            res = res & states
        return res
