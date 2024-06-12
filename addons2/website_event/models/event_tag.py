# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class EventTag(models.Model):
    _name = 'event.tag'
    _inherit = ['event.tag', 'website.published.multi.mixin']

    def default_get(self, fields_list):
        result = super().default_get(fields_list)
        if self.env.context.get('default_website_id'):
            result['website_id'] = self.env.context.get('default_website_id')
        return result
