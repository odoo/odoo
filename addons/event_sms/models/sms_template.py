# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.osv import expression


class SmsTemplate(models.Model):
    _inherit = 'sms.template'

    @api.model
    def _search_display_name(self, name,operator='ilike'):
        """Context-based hack to filter reference field in a m2o search box to emulate a domain the ORM currently does not support.

        As we can not specify a domain on a reference field, we added a context
        key `filter_template_on_event` on the template reference field. If this
        key is set, we add our domain in the `domain` in the `_search_display_name`
        method to filtrate the SMS templates.
        """
        if self.env.context.get('filter_template_on_event'):
            return [('model', '=', 'event.registration')]
        return super()._search_display_name(name, operator=operator)
