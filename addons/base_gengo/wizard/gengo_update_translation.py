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
import wrap_object as local
import logging
_logger = logging.getLogger(__name__)

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
        meta = self.pool.get('jobs.meta')
        user = self.pool.get('res.users').browse(cr, uid, uid, context)
        flag, gengo = meta.gengo_authentication(cr, uid, context)
        if flag:

            request = meta.pack_jobs_request(cr, uid, term_ids, context)
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
        meta = self.pool.get('jobs.meta')
        flag, gengo = meta.gengo_authentication(cr, uid, context)
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
        """Scheduler will be call to get response from gengo and all term will get
        by scheduler which terms are in approved state"""
        meta = self.pool.get('jobs.meta')
        translation_pool = self.pool.get('ir.translation')
        flag, gengo = meta.gengo_authentication(cr, uid, context)
        if not flag:
            _logger.warning("%s", gengo)
        else:
            translation_id = translation_pool.search(cr, uid, [('state', '=', 'inprogress'), ('gengo_translation', '=', True)], limit=local.LIMIT, context=context)
            for trns in translation_pool.browse(cr, uid, translation_id, context):
                if trns.job_id:
                    job_response = gengo.getTranslationJob(id=trns.job_id)
                    if job_response['response']['job']['status'] == 'approved':
                        translation_pool.write(cr, uid, trns.id, {'value': job_response['response']['job']['body_tgt'], 'state': 'translated', 'gengo_control': True})
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
            langs = self.pool.get('jobs.meta').check_lang_support(cr, uid, langs)
            term_ids = translation_pool.search(cr, uid, [('state', '=', 'translate'), ('gengo_translation', '=', True), ('lang', 'in', langs)], limit=local.LIMIT)
            if term_ids:
                self._send_translation_terms(cr, uid, ids, term_ids, context)
                _logger.info("Translation terms %s has been posted to gengo successfully", len(term_ids))
            else:
                _logger.info('No Translation terms to process.')
        except Exception, e:
            _logger.error("%s", e)

    _name = 'base.update.translations'
    _inherit = "base.update.translations"

base_update_translation()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
