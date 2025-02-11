# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

class BaseModel(models.AbstractModel):
    _inherit = 'base'

    def get_field_translations(self, field_name, langs=None):
        """ get model/model_term translations for records with transifex url
        :param str field_name: field name
        :param list langs: languages

        :return: (translations, context) where
            translations: list of dicts like [{"lang": lang, "source": source_term, "value": value_term,
                    "module": module, "transifexURL": transifex_url}]
            context: {"translation_type": "text"/"char", "translation_show_source": True/False}
        """
        translations, context = super().get_field_translations(field_name, langs=langs)
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
