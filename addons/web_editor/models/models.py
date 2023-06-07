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
        res = self._update_field_translations(fname, translations, lambda old_term: sha256(old_term.encode()).hexdigest())
        # The `_update_field_translations` is in charge of updating the cache
        # of the given field of the given record.
        # But this is not enough as the record might actually be used in another
        # model cached value, for instance updating the `website.menu` cache of
        # `mega_menu_content` won't be enough as it's part of the `ir.ui.view`
        # Qweb cache of compiled views, which stores the compiled value of the
        # `website.submenu` template which is looping on `website.menu`.
        # It would means that even if the cache of the `website.menu` was
        # correctly invalidated, records depending of it won't be.
        self.clear_caches()
        return res
