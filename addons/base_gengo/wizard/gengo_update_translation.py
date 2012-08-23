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


    def _send_translation_terms(self, cr, uid, ids, trg_lang, term_ids, context):
        """
        Lazy Polling will be perform when user or cron request for the trnalstion.
        """
        meta = self.pool.get('jobs.meta')
        user = self.pool.get('res.users').browse(cr, uid, uid, context)
        gengo = meta.gengo_authentication(cr, uid, ids, context)
        request = meta.pack_jobs_request(cr, uid, term_ids, trg_lang, context)
        result = gengo.postTranslationJobs(jobs=request)
        if result['opstat'] == 'ok':
            self._update_terms(cr, uid, ids, result['response'], user.company_id.gengo_tier, context)
        return True

    def do_check_schedular(self, cr, uid, xml_id, name, fn, context=None):
        cron_pool = self.pool.get('ir.cron')
        try:
            res = self.pool.get('ir.model.data')._get_id(cr, uid, 'base_gengo', xml_id)
            cron_pool.write(cr, uid, [res], {'active': True}, context)
        except:
            cron_vals.update({'name': name, "function": fn})
            return cron_pool.create(cr, uid, cron_vals, context)

    def act_update(self, cr, uid, ids, context=None):
        if context == None:
            context = {}
        lang_pool = self.pool.get('res.lang')
        for res in self.browse(cr, uid, ids, context):
            lang_id = lang_pool.search(cr, uid, [('code', '=', res.lang)])
            lang_pool.write(cr, uid, lang_id, {'gengo_sync': True})
        res = super(base_update_translation, self).act_update(cr, uid, ids, context)
        self.do_check_schedular(cr, uid, 'gengo_sync_send_request_scheduler', 'gengo_sync_send_request_scheduler', '_sync_request', context)
        self.do_check_schedular(cr, uid, 'gengo_sync_receive_request_scheduler', 'gengo_sync_send_request_scheduler', '_sync_response', context)
        return {}

    def _sync_response(self, cr, uid, ids=0, context=None):
        """Scheduler will be call to get response from gengo and all term will get
        by scheduler which terms are in approved state"""
        meta = self.pool.get('jobs.meta')
        translation_pool = self.pool.get('ir.translation')
        gengo = meta.gengo_authentication(cr, uid, ids, context)
        translation_id = translation_pool.search(cr, uid, [('job_id', '!=', False), ('state', '=', 'inprogress'), ('gengo_translation', '=', True)], limit=local.LIMIT, context=context)
        for trns in translation_pool.browse(cr, uid, translation_id, context):
            job_response = gengo.getTranslationJob(id=trns.job_id)
            if job_response['response']['job']['status'] == 'approved':
                translation_pool.write(cr, uid, translation_id, {'value': job_response['response']['job']['body_tgt'], 'state': 'translated', 'gengo_control': True})
        return True

    def _sync_request(self, cr, uid, ids=0, context=None):
        """This scheduler will send a job request to the gengo , which terms are
        in translate state and gengo_translation is true"""
        if context is None:
            context = {}
        try:
            language_pool = self.pool.get('res.lang')
            trg_lang = self.browse(cr, uid, ids)[0]
            translation_pool = self.pool.get('ir.translation')
            lang_search_id = language_pool.search(cr, uid, [('gengo_sync', '=', True), ('code', '=', trg_lang.lang)])
            if not lang_search_id:
                term_ids = translation_pool.search(cr, uid, [('state', '=', 'inprogress'), ('gengo_translation', '=', 'True'), ('lang', '=', trg_lang.lang)], limit=local.LIMIT)
                self._send_translation_terms(cr, uid, ids, trg_lang.lang, term_ids, context)
                msg = "Your Request has been Successfully Send to Gengo"
            else:
                msg = "This language is select as Active All Translation Request will be sent by System Automatically"
            context.update({'message': msg})
        except Exception, e:
            _logger.warning("%s", e)

    _name = 'base.update.translations'
    _inherit = "base.update.translations"

base_update_translation()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
