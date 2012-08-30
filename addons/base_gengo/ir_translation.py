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

from osv import fields, osv

LANG_CODE_MAPPING = {
    'ar_SA': ('ar', 'Arabic'),
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
    'pt_BR': ('pt-br', 'Portuguese (Brazil)')
}

class ir_translation(osv.Model):
    _name = "ir.translation"
    _inherit = "ir.translation"
    _columns = {
        'gengo_comment': fields.text("Comments & Activity Linked to Gengo"),
        'job_id': fields.char('Gengo JobId', size=32),
        "gengo_translation": fields.selection([('', 'Do not translate this term by Gengo'),
                                            ('machine', 'Translation By Machine'),
                                            ('standard', 'Standard'),
                                            ('pro', 'Pro'),
                                            ('ultra', 'Ultra')], "Gengo Translation Service Level", help='You can select here the service level you want for an automatic translation using Gengo.', required=True),
    }
    _defaults = {
        'gengo_translation': '',
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

    def _check_lang_support(self, cr, uid, ids, context=None):
        supported_langs = self._get_all_supported_languages(cr, uid, context=context)
        if supported_langs:
            for term in self.browse(cr, uid, ids, context=context):
                tier = "nonprofit" if term.gengo_translation == 'machine' else term.gengo_translation
                language = self._get_gengo_corresponding_language(term.lang)
                if tier not in supported_langs.get(language,[]):
                    return False
        return True

    _constraints = [
        (_check_lang_support, 'The Gengo translation service selected is not supported for this language.', ['gengo_translation'])
    ]
