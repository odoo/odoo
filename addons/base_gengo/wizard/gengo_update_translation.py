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

from osv import osv
from tools.translate import _
try:
    from mygengo import MyGengo
except ImportError:
    raise osv.except_osv(_('Gengo ImportError'), _('Please install mygengo lib from http://pypi.python.org/pypi/mygengo'))

import logging
import tools
import time
from tools.translate import _

_logger = logging.getLogger(__name__)


LIMIT = 20

LANG_MAPPING = {
    'ar': 'Arabic',
    'id': 'Indonesian',
    'nl': 'Dutch',
    'fr-ca': 'French (Canada)',
    'pl': 'Polish',
    'zh-tw': 'Chinese (Traditional)',
    'sv': 'Swedish',
    'ko': 'Korean',
    'pt': 'Portuguese (Europe)',
    'en': 'English',
    'ja': 'Japanese',
    'es': 'Spanish (Spain)',
    'zh': 'Chinese (Simplified)',
    'de': 'German',
    'fr': 'French',
    'ru': 'Russian',
    'it': 'Italian',
    'pt-br': 'Portuguese (Brazil)',
}

LANG_CODE_MAPPING = {
    'ar_SA': 'ar',
    'id_ID': 'id',
    'nl_NL': 'nl',
    'fr_CA': 'fr-ca',
    'pl': 'pl',
    'zh_TW': 'zh-tw',
    'sv_SE': 'sv',
    'ko_KR': 'ko',
    'pt_PT': 'pt',
    'en_US': 'en',
    'ja_JP': 'ja',
    'es_ES': 'es',
    'zh_CN': 'zh',
    'de_DE': 'de',
    'fr_FR': 'fr',
    'fr_BE': 'fr',
    'ru_RU': 'ru',
    'it_IT': 'it',
    'pt_BR': 'pt-br'
}

cron_vals = {
    'name': 'Gengo Sync',
    'active': True,
    'interval_number': 30,
    'interval_type': 'minutes',
    'numbercall': -1,
    'model': "'base.update.translations'",
    'function': ""
}


class base_update_translation(osv.osv_memory):

    _name = 'base.update.translations'
    _inherit = "base.update.translations"

    def gengo_authentication(self, cr, uid, context=None):
        ''' To Send Request and Get Response from Gengo User needs Public and Private
         key for that user need to signup to gengo and get public and private
         key which is provided by gengo to authentic user '''

        user = self.pool.get('res.users').browse(cr, uid, uid, context)
        if not user.company_id.gengo_public_key or not user.company_id.gengo_private_key:
            return (False, "Invalid gengo configuration.\nEither pulic key or private key is missing.")
        try:
            gengo = MyGengo(
                public_key=user.company_id.gengo_public_key.encode('ascii'),
                private_key=user.company_id.gengo_private_key.encode('ascii'),
                sandbox=True,
            )
            gengo.getAccountStats()
            return (True, gengo)
        except Exception, e:
            return (False, "Gengo Connection Error\n"+e.message)

    def pack_jobs_request(self, cr, uid, term_ids, context):
        jobs = {}
        auto_approve = 0
        gengo_parameter_pool = self.pool.get('res.users').browse(cr, uid, uid, context)
        translation_pool = self.pool.get('ir.translation')
        if gengo_parameter_pool.company_id.gengo_auto_approve:
            auto_approve = 1
        for term in translation_pool.browse(cr, uid, term_ids, context):
            if term.src and term.src != "":
                job = {'type': 'text',
                        'slug': 'single::English to' + LANG_CODE_MAPPING[term.lang],
                        'tier': tools.ustr(gengo_parameter_pool.company_id.gengo_tier),
                        'body_src': term.src,
                        'lc_src': 'en',
                        'lc_tgt': LANG_CODE_MAPPING[term.lang],
                        'auto_approve': auto_approve,
                        'comment': gengo_parameter_pool.company_id.gengo_comment,
                }
                jobs.update({term.id: job})
        return {'jobs': jobs}

    def check_lang_support(self, cr, uid, langs, context=None):
        new_langs = []
        flag, gengo = self.gengo_authentication(cr, uid, context)
        if not flag:
            return []
        else:
            user = self.pool.get('res.users').browse(cr, uid, uid, context)
            tier = user.company_id.gengo_tier
            if tier == "machine":
                tier = "nonprofit"

            lang_pair = gengo.getServiceLanguagePairs(lc_src='en')
            if lang_pair['opstat'] == 'ok':
                for g_lang in lang_pair['response']:
                    for l in langs:
                        if LANG_CODE_MAPPING[l] == g_lang['lc_tgt'] and g_lang['tier'] == tier:
                            new_langs.append(l)
            return list(set(new_langs))
    def _update_terms(self, cr, uid, ids, response, tier, context):
        translation_pool = self.pool.get('ir.translation')
        for jobs in response['jobs']:
            vals = {}
            for t_id, res in jobs.items():
                if tier == "machine":
                    vals.update({'value': res['body_tgt'], 'state': 'translated'})
                else:
                    vals.update({'job_id': res['job_id'], 'state': 'inprogress'})
                translation_pool.write(cr, uid, [t_id], vals, context)
        return

    def _send_translation_terms(self, cr, uid, ids, term_ids, context):
        """
        Lazy Polling will be perform when user or cron request for the trnalstion.
        """
        user = self.pool.get('res.users').browse(cr, uid, uid, context)
        flag, gengo = self.gengo_authentication(cr, uid, context)
        if flag:

            request = self.pack_jobs_request(cr, uid, term_ids, context)
            if request:
                result = gengo.postTranslationJobs(jobs=request)
                if result['opstat'] == 'ok':
                    self._update_terms(cr, uid, ids, result['response'], user.company_id.gengo_tier, context)
        else:
            _logger.error(gengo)
        return True

    def do_check_schedular(self, cr, uid, xml_id, name, fn, context=None):
        cron_pool = self.pool.get('ir.cron')
        try:
            res = []
            model, res = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'base_gengo', xml_id)
            cron_pool.write(cr, uid, [res], {'active': True}, context=context)
        except:
            cron_vals.update({'name': name, "function": fn})
            return cron_pool.create(cr, uid, cron_vals, context)

    def act_update(self, cr, uid, ids, context=None):
        if context == None:
            context = {}
        lang_pool = self.pool.get('res.lang')
        super(base_update_translation, self).act_update(cr, uid, ids, context)
        msg = "1. Translation file loaded succesfully.\n2. Processing Gengo Translation:\n"
        flag, gengo = self.gengo_authentication(cr, uid, context)
        if not flag:
            msg += gengo
        else:
            for res in self.browse(cr, uid, ids, context):
                lang_id = lang_pool.search(cr, uid, [('code', '=', res.lang)])
                lang_search = lang_pool.search(cr, uid, [('gengo_sync', '=', True),
                ('id', '=', lang_id[0])])
                if lang_search:
                    msg += 'This language %s is alreay in queue for processing.' % (res.lang)
                else:
                    msg += "Translation for language %s is queued for processing." % (res.lang)
                    lang_pool.write(cr, uid, lang_id, {'gengo_sync': True})
                    _logger.info("Your translation request for language '%s' has been send sucessfully.", res.lang)

                self.do_check_schedular(cr, uid, 'gengo_sync_send_request_scheduler', 'Gengo Sync Translation (Request)', '_sync_request', context)
                self.do_check_schedular(cr, uid, 'gengo_sync_receive_request_scheduler', 'Gengo Sync Translation (Response)', '_sync_response', context)
                self._sync_request(cr, uid, ids, context)
        context.update({'message': msg})
        obj_model = self.pool.get('ir.model.data')
        model_data_ids = obj_model.search(cr, uid, [('model', '=', 'ir.ui.view'), ('name', '=', 'update_translation_wizard_view_confirm')])
        view_id = obj_model.read(cr, uid, model_data_ids, fields=['res_id'], context=context)[0]['res_id']
        return {
                 'view_type': 'form',
                 'view_mode': 'form',
                 'res_model': 'gengo.update.message',
                 'views': [(view_id, 'form')],
                 'type': 'ir.actions.act_window',
                 'target': 'new',
                 'context': context,
             }

    def _sync_response(self, cr, uid, ids=False, context=None):
        """
        This method  will be call by cron services to get translation from
        gengo for translation terms which are posted to be translated. It will
        read translated terms and comments from gengo and will update respective
        translation in openerp """
        translation_pool = self.pool.get('ir.translation')
        flag, gengo = self.gengo_authentication(cr, uid, context)
        if not flag:
            _logger.warning("%s", gengo)
        else:
            translation_id = translation_pool.search(cr, uid, [('state', '=', 'inprogress'), ('gengo_translation', '=', True)], limit=LIMIT, context=context)
            for term in translation_pool.browse(cr, uid, translation_id, context):
                if term.job_id:
                    vals={}
                    job_response = gengo.getTranslationJob(id=term.job_id)
                    if job_response['opstat'] != 'ok':
                        _logger.warning("Invalid Response Skeeping translation Terms for 'id' %s."%(term.job_id))
                        continue
                    if job_response['response']['job']['status'] == 'approved':
                        vals.update({'state': 'translated',
                            'value': job_response['response']['job']['body_tgt'],
                            'gengo_control': True})
                    job_comment = gengo.getTranslationJobComments(id=term.job_id)
                    if job_comment['opstat']=='ok':
                        gengo_comments=""
                        for comment in job_comment['response']['thread']:
                            gengo_comments+='%s by %s at %s. \n'    %(comment['body'],comment['author'],time.ctime(comment['ctime']))
                        vals.update({'gengo_comment':gengo_comments})
                    if vals:
                        translation_pool.write(cr, uid, term.id,vals)
        return True

    def _sync_request(self, cr, uid, ids=False, context=None):
        """This scheduler will send a job request to the gengo , which terms are
        in translate state and gengo_translation is true"""
        if context is None:
            context = {}
        language_pool = self.pool.get('res.lang')
        translation_pool = self.pool.get('ir.translation')
        try:
            lang_ids = language_pool.search(cr, uid, [('gengo_sync', '=', True)])
            langs = [lang.code for lang in language_pool.browse(cr, uid, lang_ids)]
            langs = self.check_lang_support(cr, uid, langs)
            term_ids = translation_pool.search(cr, uid, [('state', '=', 'translate'), ('gengo_translation', '=', True), ('lang', 'in', langs)], limit=LIMIT)
            if term_ids:
                self._send_translation_terms(cr, uid, ids, term_ids, context)
                _logger.info("Translation terms %s has been posted to gengo successfully", len(term_ids))
            else:
                _logger.info('No Translation terms to process.')
        except Exception, e:
            _logger.error("%s", e)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
