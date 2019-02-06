# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api

class Partner(models.Model):
    _inherit = "res.partner"

    @api.model
    def _commercial_fields(self):
        """ According to the CGST Act, Suppliers of taxable goods and services are required to be registered under
            GST in the State or Union territory, from where the taxable supply of goods or services is made.
            Also, in case of more than one GST registration within a state, the entity code would also change."""
        res = super(Partner, self)._commercial_fields()
        if self.country_id and self.country_id.code == 'IN':
            res.remove('vat')
        return res
