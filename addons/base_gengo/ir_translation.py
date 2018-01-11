# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (C) 2004-2012 OpenERP S.A. (<http://openerp.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import fields, osv
from openerp.tools.translate import _

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


class ir_translation(osv.Model):
    _name = "ir.translation"
    _inherit = "ir.translation"

    _columns = {
        'gengo_comment': fields.text("Comments & Activity Linked to Gengo"),
        'order_id': fields.char('Gengo Order ID', size=32),
        "gengo_translation": fields.selection([('machine', 'Translation By Machine'),
                                             ('standard', 'Standard'),
                                             ('pro', 'Pro'),
                                             ('ultra', 'Ultra')], "Gengo Translation Service Level", help='You can select here the service level you want for an automatic translation using Gengo.'),
    }

    def _get_all_supported_languages(self, cr, uid, context=None):
        flag, gengo = self.pool.get('base.gengo.translations').gengo_authentication(cr, uid, context=context)
        if not flag:
            raise osv.except_osv(_('Gengo Authentication Error'), gengo)
        supported_langs = {}
        lang_pair = gengo.getServiceLanguagePairs(lc_src='en')
        if lang_pair['opstat'] == 'ok':
            for g_lang in lang_pair['response']:
                if g_lang['lc_tgt'] not in supported_langs:
                    supported_langs[g_lang['lc_tgt']] = []
                supported_langs[g_lang['lc_tgt']] += [g_lang['tier']]
        return supported_langs

    def _get_gengo_corresponding_language(cr, lang):
        return lang in LANG_CODE_MAPPING and LANG_CODE_MAPPING[lang][0] or lang

    def _get_source_query(self, cr, uid, name, types, lang, source, res_id):
        query, params = super(ir_translation, self)._get_source_query(cr, uid, name, types, lang, source, res_id)

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
