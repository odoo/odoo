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
import wrap_object
import logging
_logger = logging.getLogger(__name__)


class gengo_update_translation(osv.osv_memory):

    def send_translation_terms(self, cr, uid, ids, context):
        """Lasy Loading will be perform when user or cron send a bunch of request."""
        total_term = 0
        limit = 0
        translation_list = context['translation_term_id']
        range_jobs = 1
        meta = self.pool.get('jobs.meta')
        translation_pool = self.pool.get('ir.translation')
        user = self.pool.get('res.users').browse(cr, uid, uid, context)
        gengo = meta.gengo_authentication(cr, uid, ids, context)
        job_length = len(context['translation_term_id'])
        remain = len(context['translation_term_id']) % wrap_object.REQUEST_LIMIT
        if len(context['translation_term_id']) > wrap_object.REQUEST_LIMIT:
            if remain > 0:
                range_jobs = (len(context['translation_term_id']) / wrap_object.REQUEST_LIMIT) + 1
            else:
                range_jobs = len(context['translation_term_id']) / wrap_object.REQUEST_LIMIT
        for length in range(0, range_jobs):
            trans_list = []
            if job_length > wrap_object.REQUEST_LIMIT:
                job_length -= wrap_object.REQUEST_LIMIT
                limit += wrap_object.REQUEST_LIMIT
            else:
                limit += remain
            for key in translation_list[total_term:limit]:
                trans_list.append(key)
            total_term = limit
            request = meta.pack_jobs_request(cr, uid, trans_list, context={'language_code': context['lang']})
            result = gengo.postTranslationJobs(jobs=request)
            if user.company_id.gengo_tier == 'machine':
                response = meta.unpack_jobs_response(result)
                for job in response.response[1]:
                    for jobs in job:
                        translation_term_id = translation_pool.search(cr, uid, [('src', '=', job[jobs]['body_src'])])
                        translation_pool.write(cr, uid, translation_term_id, {'value': job[jobs]['body_tgt'], 'state': 'translated', 'gengo_control': True})
            return

    def act_update(self, cr, uid, ids, context=None):
        if context == None:
            context={}
        try:
            language_pool = self.pool.get('res.lang')
            this = self.browse(cr, uid, ids)[0]
            translation_pool = self.pool.get('ir.translation')
            lang_search_id = language_pool.search(cr, uid,
            [('gengo_sync', '=', True), ('code', '=', this.lang)])

            if not lang_search_id:
                translation_term_id = translation_pool.search(cr, uid, [('state', '=', 'translate'), ('gengo_translation', '=', 'True'), ('lang', '=', this.lang)])
                context.update({'lang': this.lang, 'translation_term_id': translation_term_id})
                self.send_translation_terms(cr, uid, ids, context)
                msg = "Your Request has been Successfully Send to Gengo"
            else:
                msg = "This language is select as Active All Translation Request will be sent by System Automatically"

        except Exception, e:
            msg = '%s' % e
        context.update({'message': msg})
        obj_model = self.pool.get('ir.model.data')
        model_data_ids = obj_model.search(cr, uid, [('model', '=', 'ir.ui.view'), ('name', '=', 'update_translation_wizard_view_confirm')])
        resource_id = obj_model.read(cr, uid, model_data_ids, fields=['res_id'], context=context)[0]['res_id']
        return {
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'gengo.update.message',
                'views': [(resource_id, 'form')],
                'type': 'ir.actions.act_window',
                'target': 'new',
               'context': context,
            }

    def scheduler_get_gengo_response(self, cr, uid, ids=0, context=None):
        """Scheduler will be call to get response from gengo and all term will get
        by scheduler which terms are in reviewable state"""
        meta = self.pool.get('jobs.meta')
        translation_pool = self.pool.get('ir.translation')
        gengo = meta.gengo_authentication(cr, uid, ids, context)
        res = gengo.getTranslationJobs(status="approved")
        if res:
            response = meta.unpack_jobs_response(res)
            for job in response.response:
                job_response=gengo.getTranslationJob(id=job['job_id'])
                jobs_response = meta.unpack_jobs_response(job_response)
                translation_id = translation_pool.search(cr, uid, [('src', '=', jobs_response.response[0]['body_src'])], context)
                translation_pool.write(cr, uid, translation_id, {'value': jobs_response.response[0]['body_tgt'], 'state': 'translated', 'gengo_control': True})

    def scheduler_get_gengo_sync_request(self, cr, uid, ids=0, context=None):
        """This scheduler will send a job request to the gengo , which terms are
        in translate state and gengo_translation is true"""

        if context is None:
            context = {}
        try:
            language_pool = self.pool.get('res.lang')
            translation_pool = self.pool.get('ir.translation')
            lang_search_id = language_pool.search(cr, uid, [('gengo_sync', '=', True)])
            lang_ids = language_pool.read(cr, uid, lang_search_id)

            for lang_id in lang_ids:
                translation_term_id = translation_pool.search(cr, uid, [('state', '=', 'translate'), ('gengo_translation', '=', 'True'), ('lang', '=', lang_id['code'])])
                context.update({'lang': lang_id['code'], 'translation_term_id':  translation_term_id})
                if translation_term_id:
                    self.send_translation_terms(cr, uid, ids, context)
        except Exception, e:
            _logger.warning('A Gengo Exception is occur:: %s', e)

    _name = 'base.update.translations'
    _inherit = "base.update.translations"

gengo_update_translation()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
