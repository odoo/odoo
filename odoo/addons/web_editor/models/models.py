# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from hashlib import sha256

from odoo import api, models


class Base(models.AbstractModel):
    _inherit = 'base'

    @api.model
    def _get_view_field_attributes(self):
        keys = super()._get_view_field_attributes()
        keys.append('sanitize')
        keys.append('sanitize_tags')
        return keys


class BaseModel(models.AbstractModel):
    _inherit = 'base'

    def update_field_translations_sha(self, fname, translations):
        field = self._fields[fname]
        if callable(field.translate):
            for translation in translations.values():
                for key, value in translation.items():
                    translation[key] = field.translate.term_converter(value)
        return self._update_field_translations(fname, translations, lambda old_term: sha256(old_term.encode()).hexdigest())
