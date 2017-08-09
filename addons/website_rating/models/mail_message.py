# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class MailMessage(models.Model):
    _inherit = 'mail.message'

    @api.multi
    def website_message_format(self):
        result = super(MailMessage, self).website_message_format()
        # inlude rating value in data if requested
        if self._context.get('rating_include'):
            message_data = self.read(['rating_value'])
            message_tree = dict((m['id'], m['rating_value']) for m in message_data)
            for message_vals in result:
                message_vals['rating_value'] = message_tree.get(message_vals['id'], False)  # False for no rating
        return result
