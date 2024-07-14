# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def action_partner_navigate(self):
        self.ensure_one()
        if not self.partner_latitude or not self.partner_longitude:
            self.geo_localize()
        url = "https://www.google.com/maps/dir/?api=1&destination=%s,%s" % (self.partner_latitude, self.partner_longitude)
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new'
        }
