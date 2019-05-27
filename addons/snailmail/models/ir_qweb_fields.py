# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models


class Contact(models.AbstractModel):
    _inherit = 'ir.qweb.field.contact'

    @api.model
    def value_to_html(self, value, options):
        if self.env.context.get('snailmail_layout'):
           value = value.with_context(snailmail_layout=self.env.context['snailmail_layout'])
        return super(Contact, self).value_to_html(value, options)

    @api.model
    def record_to_html(self, record, field_name, options):
        if self.env.context.get('snailmail_layout'):
           record = record.with_context(snailmail_layout=self.env.context['snailmail_layout'])
        return super(Contact, self).record_to_html(record, field_name, options)
