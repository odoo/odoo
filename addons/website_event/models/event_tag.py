# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class EventTag(models.Model):
    _name = 'event.tag'
    _inherit = ['event.tag', 'website.published.multi.mixin']

    @api.model
    def default_get(self, fields):
        result = super().default_get(fields)
        if self.env.context.get('default_website_id'):
            result['website_id'] = self.env.context.get('default_website_id')
        return result
