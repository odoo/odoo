# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import UserError

LANG_CODE_MAPPING = {
    'ar_SY': ('ar', 'Arabic'),
    'id_ID': ('id', 'Indonesian'),
    'nl_NL': ('nl', 'Dutch'),
    'fr_CA': ('fr-ca', 'French (Canada)'),
    'pl_PL': ('pl', 'Polish'),
    'zh_TW': ('zh-tw', 'Chinese (Traditional)'),
    'sv_SE': ('sv', 'Swedish'),
    'ko_KR': ('ko', 'Korean'),
    'pt_PT': ('pt', 'Portuguese (Europe)'),
    'en_US': ('en', 'English'),
    'ja_JP': ('ja', 'Japanese'),
    'es_ES': ('es', 'Spanish (Spain)'),
    'zh_CN': ('zh', 'Chinese (Simplified)'),
    'de_DE': ('de', 'German'),
    'fr_FR': ('fr', 'French'),
    'fr_BE': ('fr', 'French'),
    'ru_RU': ('ru', 'Russian'),
    'it_IT': ('it', 'Italian'),
    'pt_BR': ('pt-br', 'Portuguese (Brazil)'),
    'th_TH': ('th', 'Thai'),
    'nb_NO': ('no', 'Norwegian'),
    'ro_RO': ('ro', 'Romanian'),
    'tr_TR': ('tr', 'Turkish'),
    'bg_BG': ('bg', 'Bulgarian'),
    'da_DK': ('da', 'Danish'),
    'en_GB': ('en-gb', 'English (British)'),
    'el_GR': ('el', 'Greek'),
    'vi_VN': ('vi', 'Vietnamese'),
    'he_IL': ('he', 'Hebrew'),
    'hu_HU': ('hu', 'Hungarian'),
    'fi_FI': ('fi', 'Finnish')
}


class IrTranslation(models.Model):
    _inherit = "ir.translation"

    gengo_comment = fields.Text("Comments & Activity Linked to Gengo")
    order_id = fields.Char('Gengo Order ID')
    gengo_translation = fields.Selection([
        ('machine', 'Translation By Machine'),
        ('standard', 'Standard'),
        ('pro', 'Pro'),
        ('ultra', 'Ultra')
        ], "Gengo Translation Service Level",
        help='You can select here the service level you want for an automatic translation using Gengo.')

    @api.model
    def _get_all_supported_languages(self):
        flag, gengo = self.env['base.gengo.translations'].gengo_authentication()
        if not flag:
            raise UserError(gengo)
        supported_langs = {}
        lang_pair = gengo.getServiceLanguagePairs(lc_src='en')
        if lang_pair['opstat'] == 'ok':
            for g_lang in lang_pair['response']:
                if g_lang['lc_tgt'] not in supported_langs:
                    supported_langs[g_lang['lc_tgt']] = []
                supported_langs[g_lang['lc_tgt']] += [g_lang['tier']]
        return supported_langs

    def _get_gengo_corresponding_language(self, lang):
        return lang in LANG_CODE_MAPPING and LANG_CODE_MAPPING[lang][0] or lang

    @api.model
    def _get_source_query(self, name, types, lang, source, res_id):
        query, params = super(IrTranslation, self)._get_source_query(name, types, lang, source, res_id)

        # disable gengo during module installation and uninstallation
        if not self.pool.ready:
            return query, params

        query += """
                    ORDER BY
                        CASE
                            WHEN gengo_translation=%s then 10
                            WHEN gengo_translation=%s then 20
                            WHEN gengo_translation=%s then 30
                            WHEN gengo_translation=%s then 40
                            ELSE 0
                        END DESC
                 """
        params += ('machine', 'standard', 'ultra', 'pro',)
        return (query, params)

    @api.model
    def _get_terms_query(self, field, records):
        query, params = super(IrTranslation, self)._get_terms_query(field, records)

        # disable gengo during module installation and uninstallation
        if not self.pool.ready:
            return query, params

        # order translations from worst to best
        query += """
                    ORDER BY
                        CASE
                            WHEN gengo_translation=%s then 10
                            WHEN gengo_translation=%s then 20
                            WHEN gengo_translation=%s then 30
                            WHEN gengo_translation=%s then 40
                            ELSE 0
                        END ASC
                 """
        params += ('machine', 'standard', 'ultra', 'pro')
        return query, params
