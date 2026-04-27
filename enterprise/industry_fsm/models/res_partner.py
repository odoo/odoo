# Part of Odoo. See LICENSE file for full copyright and licensing details.

import urllib.parse

from odoo import models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def action_partner_navigate(self):
        self.ensure_one()
        encoded_address = urllib.parse.quote_plus(self.contact_address_complete)
        url = f"https://www.google.com/maps/dir/?api=1&destination={encoded_address}"
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new'
        }
