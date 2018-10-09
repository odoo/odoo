# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models


class Contact(models.AbstractModel):
    _inherit = 'ir.qweb.field.contact'

    @api.model
    def value_to_html(self, value, options):
        snailmail_layout = options['template_options'].get('snailmail_layout')
        value = value.with_context(snailmail_layout=snailmail_layout)
        return super(Contact, self).value_to_html(value, options)
