# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _


class Field(models.AbstractModel):
    _inherit = 'ir.qweb.field'

    @api.model
    def attributes(self, record, field_name, options, values):
        attrs = super().attributes(record, field_name, options, values)

        if field_name == 'teaser' and self.env.context.get('edit_translations'):
            attrs['data-translate-error-tooltip'] = _("On your default language, empty the blog post description and save to get an automated (translated) summary.")

        return attrs
