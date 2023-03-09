# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

class BaseModel(models.AbstractModel):
    _inherit = 'base'

    def get_field_translations(self, field_name):
        """ get model/model_term translations for records with transifex url
        :param str field_name: field name
        :param list langs: languages

        :return: (translations, context) where
            translations: list of dicts like [{"lang": lang, "source": source_term, "value": value_term, "is_translated": True/False,
                    "module": module, "transifex_url": transifex_url}]
            context: {"field_type": field.type, "translate_type": "model"/"model_terms"}
        """
        translations, context = super().get_field_translations(field_name)
        external_id = self.get_external_id().get(self.id)
        if not external_id:
            return translations, context

        module = external_id.split('.')[0]
        if module not in self.pool._init_modules:
            return translations, context

        for translation in translations:
            translation['module'] = module
        self.env['transifex.translation']._update_transifex_url(translations)
        return translations, context
