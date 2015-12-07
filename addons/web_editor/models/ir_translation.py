# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

class IrTranslation(models.Model):
    _inherit = 'ir.translation'

    def _get_terms_mapping(self, field, records):
        if self.env.context.get('edit_translations'):
            self.insert_missing(field, records)
            return lambda data: '<span data-oe-translation-id="%(id)s" data-oe-translation-state="%(state)s">%(value)s</span>' % data
        return super(IrTranslation, self)._get_terms_mapping(field, records)
