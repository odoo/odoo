# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    website_id = fields.Many2one(
        'website', related='partner_id.website_id', string='Website',
        help='Website through which this invoice was created for eCommerce orders.',
        store=True, readonly=True, tracking=True)

    def preview_invoice(self):
        action = super().preview_invoice()
        if action['url'].startswith('/'):
            # URL should always be relative, safety check
            action['url'] = f'/@{action["url"]}'
        return action
