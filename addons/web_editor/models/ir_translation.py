# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import models, api

def edit_translation_mapping(data):
    data = dict(data, model=data['name'].partition(',')[0])
    return '<span data-oe-model="%(model)s" data-oe-translation-id="%(id)s" data-oe-translation-state="%(state)s">%(value)s</span>' % data

class ir_translation(models.Model):
    _inherit = 'ir.translation'

    @api.model
    def _get_terms_mapping(self, field, records):
        if self._context.get('edit_translations'):
            self.insert_missing(field, records)
            return edit_translation_mapping
        return super(ir_translation, self)._get_terms_mapping(field, records)
