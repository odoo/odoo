# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class MailMessage(models.Model):
    _inherit = 'mail.message'

    @api.multi
    def _portal_message_format(self, field_list):
        # inlude rating value in data if requested
        if self._context.get('rating_include'):
            field_list += ['rating_value']
        return super(MailMessage, self)._portal_message_format(field_list)
