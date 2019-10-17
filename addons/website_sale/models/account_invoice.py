# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    website_id = fields.Many2one('website', related='partner_id.website_id', string='Website',
                                 help='Website through which this invoice was created.',
                                 store=True, readonly=True)

    @api.multi
    def get_base_url(self):
        """When using multi-website, we want the user to be redirected to the
        most appropriate website if possible."""
        res = super(AccountInvoice, self).get_base_url()
        return self.website_id and self.website_id._get_http_domain() or res
