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

import uuid
import logging
import re
import time

from openerp.osv import osv, fields
from openerp import tools, SUPERUSER_ID
from openerp.tools.translate import _

_logger = logging.getLogger(__name__)

try:
    from gengo import Gengo
except ImportError:
    _logger.warning('Gengo library not found, Gengo features disabled. If you plan to use it, please install the gengo library from http://pypi.python.org/pypi/gengo')

GENGO_DEFAULT_LIMIT = 20


class base_gengo_translations(osv.osv_memory):
    GENGO_KEY = "Gengo.UUID"
    GROUPS = ['base.group_system']

    _name = 'base.gengo.translations'
    _columns = {
        'sync_type': fields.selection([('send', 'Send New Terms'),
                                       ('receive', 'Receive Translation'),
                                       ('both', 'Both')], "Sync Type", required=True),
        'lang_id': fields.many2one('res.lang', 'Language', required=True),
        'sync_limit': fields.integer("No. of terms to sync"),
    }
    _defaults = {
        'sync_type': 'both',
        'sync_limit': 20
    }

    def init(self, cr):
        icp = self.pool['ir.config_parameter']
        if not icp.get_param(cr, SUPERUSER_ID, self.GENGO_KEY, default=None):
            icp.set_param(cr, SUPERUSER_ID, self.GENGO_KEY, str(uuid.uuid4()), groups=self.GROUPS)

    def get_gengo_key(self, cr):
        icp = self.pool['ir.config_parameter']
        return icp.get_param(cr, SUPERUSER_ID, self.GENGO_KEY, default="Undefined")

    def gengo_authentication(self, cr, uid, context=None):
        '''
        This method tries to open a connection with Gengo. For that, it uses the Public and Private
        keys that are linked to the company (given by Gengo on subscription). It returns a tuple with
         * as first element: a boolean depicting if the authentication was a success or not
         * as second element: the connection, if it was a success, or the error message returned by
            Gengo when the connection failed.
            This error message can either be displayed in the server logs (if the authentication was called
            by the cron) or in a dialog box (if requested by the user), thus it's important to return it
            translated.
        '''
        user = self.pool.get('res.users').browse(cr, 1, uid, context=context)
        if not user.company_id.gengo_public_key or not user.company_id.gengo_private_key:
            return (False, _("Gengo `Public Key` or `Private Key` are missing. Enter your Gengo authentication parameters under `Settings > Companies > Gengo Parameters`."))
        try:
            gengo = Gengo(
                public_key=user.company_id.gengo_public_key.encode('ascii'),
                private_key=user.company_id.gengo_private_key.encode('ascii'),
                sandbox=user.company_id.gengo_sandbox,
            )
            gengo.getAccountStats()
            return (True, gengo)
        except Exception, e:
            _logger.exception('Gengo connection failed')
            return (False, _("Gengo connection failed with this message:\n``%s``") % e)

    def act_update(self, cr, uid, ids, context=None):
        '''
        Function called by the wizard.
        '''
        if context is None:
            context = {}

        flag, gengo = self.gengo_authentication(cr, uid, context=context)
        if not flag:
            raise osv.except_osv(_('Gengo Authentication Error'), gengo)
        for wizard in self.browse(cr, uid, ids, context=context):
            supported_langs = self.pool.get('ir.translation')._get_all_supported_languages(cr, uid, context=context)
            language = self.pool.get('ir.translation')._get_gengo_corresponding_language(wizard.lang_id.code)
            if language not in supported_langs:
                raise osv.except_osv(_("Warning"), _('This language is not supported by the Gengo translation services.'))

            ctx = context.copy()
            ctx['gengo_language'] = wizard.lang_id.id
            if wizard.sync_limit > 200 or wizard.sync_limit < 1:
                raise osv.except_osv(_("Warning"), _('Sync limit should between 1 to 200 for Gengo translation services.'))
            if wizard.sync_type in ['send', 'both']:
                self._sync_request(cr, uid, wizard.sync_limit, context=ctx)
            if wizard.sync_type in ['receive', 'both']:
                self._sync_response(cr, uid, wizard.sync_limit, context=ctx)
        return {'type': 'ir.actions.act_window_close'}

    def _sync_response(self, cr, uid, limit=GENGO_DEFAULT_LIMIT, context=None):
        """
        This method will be called by cron services to get translations from
        Gengo. It will read translated terms and comments from Gengo and will
        update respective ir.translation in Odoo.
        """
        translation_pool = self.pool.get('ir.translation')
        flag, gengo = self.gengo_authentication(cr, uid, context=context)
        if not flag:
            _logger.warning("%s", gengo)
        else:
            offset = 0
            all_translation_ids = translation_pool.search(cr, uid, [('state', '=', 'inprogress'), ('gengo_translation', 'in', ('machine', 'standard', 'pro', 'ultra')), ('order_id', "!=", False)], context=context)
            while True:
                translation_ids = all_translation_ids[offset:offset + limit]
                offset += limit
                if not translation_ids:
                    break

                terms_progress = {
                    'gengo_order_ids': set(),
                    'ir_translation_ids': set(),
                }
                translation_terms = translation_pool.browse(cr, uid, translation_ids, context=context)
                for term in translation_terms:
                    terms_progress['gengo_order_ids'].add(term.order_id)
                    terms_progress['ir_translation_ids'].add(tools.ustr(term.id))

                for order_id in terms_progress['gengo_order_ids']:
                    order_response = gengo.getTranslationOrderJobs(id=order_id)
                    jobs_approved = order_response.get('response', []).get('order', []).get('jobs_approved', [])
                    gengo_ids = ','.join(jobs_approved)

                if gengo_ids:  # Need to check, because getTranslationJobBatch don't catch this case and so call the getTranslationJobs because no ids in url
                    try:
                        job_response = gengo.getTranslationJobBatch(id=gengo_ids)
                    except:
                        continue
                    if job_response['opstat'] == 'ok':
                        for job in job_response['response'].get('jobs', []):
                            if job.get('custom_data') in terms_progress['ir_translation_ids']:
                                self._update_terms_job(cr, uid, job, context=context)
        return True

    def _update_terms_job(self, cr, uid, job, context=None):
        translation_pool = self.pool.get('ir.translation')
        tid = int(job['custom_data'])
        vals = {}
        if job.get('status', False) in ('queued', 'available', 'pending', 'reviewable'):
            vals['state'] = 'inprogress'
        if job.get('body_tgt', False) and job.get('status', False) == 'approved':
            vals['value'] = job['body_tgt']
        if job.get('status', False) in ('approved', 'canceled'):
            vals['state'] = 'translated'
        if vals:
            translation_pool.write(cr, uid, [tid], vals, context=context)

    def _update_terms(self, cr, uid, response, term_ids, context=None):
        """
        Update the terms after their translation were requested to Gengo
        """
        translation_pool = self.pool.get('ir.translation')

        vals = {
            'order_id': response.get('order_id', ''),
            'state': 'inprogress'
        }

        translation_pool.write(cr, uid, term_ids, vals, context=context)
        jobs = response.get('jobs', [])
        if jobs:
            for t_id, res in jobs.items():
                self._update_terms_job(cr, uid, res, context=context)

        return

    def pack_jobs_request(self, cr, uid, term_ids, context=None):
        ''' prepare the terms that will be requested to gengo and returns them in a dictionary with following format
            {'jobs': {
                'term1.id': {...}
                'term2.id': {...}
                }
            }'''
        base_url = self.pool.get('ir.config_parameter').get_param(cr, uid, 'web.base.url')
        translation_pool = self.pool.get('ir.translation')
        jobs = {}
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        auto_approve = 1 if user.company_id.gengo_auto_approve else 0
        for term in translation_pool.browse(cr, uid, term_ids, context=context):
            if re.search(r"\w", term.src or ""):
                comment = user.company_id.gengo_comment or ''
                if term.gengo_comment:
                    comment += '\n' + term.gengo_comment
                jobs[time.strftime('%Y%m%d%H%M%S') + '-' + str(term.id)] = {
                    'type': 'text',
                    'slug': 'Single :: English to ' + term.lang,
                    'tier': tools.ustr(term.gengo_translation),
                    'custom_data': str(term.id),
                    'body_src': term.src,
                    'lc_src': 'en',
                    'lc_tgt': translation_pool._get_gengo_corresponding_language(term.lang),
                    'auto_approve': auto_approve,
                    'comment': comment,
                    'callback_url': "%s/website/gengo_callback?pgk=%s&db=%s" % (base_url, self.get_gengo_key(cr), cr.dbname)
                }
        return {'jobs': jobs, 'as_group': 0}

    def _send_translation_terms(self, cr, uid, term_ids, context=None):
        """
        Send a request to Gengo with all the term_ids in a different job, get the response and update the terms in
        database accordingly.
        """
        flag, gengo = self.gengo_authentication(cr, uid, context=context)
        if flag:
            request = self.pack_jobs_request(cr, uid, term_ids, context=context)
            if request['jobs']:
                result = gengo.postTranslationJobs(jobs=request)
                if result['opstat'] == 'ok':
                    self._update_terms(cr, uid, result['response'], term_ids, context=context)
        else:
            _logger.error(gengo)
        return True

    def _sync_request(self, cr, uid, limit=GENGO_DEFAULT_LIMIT, context=None):
        """
        This scheduler will send a job request to the gengo , which terms are
        waiing to be translated and for which gengo_translation is enabled.

        A special key 'gengo_language' can be passed in the context in order to
        request only translations of that language only. Its value is the language
        ID in Odoo.
        """
        if context is None:
            context = {}
        language_pool = self.pool.get('res.lang')
        translation_pool = self.pool.get('ir.translation')
        domain = [('state', '=', 'to_translate'), ('gengo_translation', 'in', ('machine', 'standard', 'pro', 'ultra')), ('order_id', "=", False)]
        if context.get('gengo_language', False):
            lc = language_pool.browse(cr, uid, context['gengo_language'], context=context).code
            domain.append(('lang', '=', lc))

        all_term_ids = translation_pool.search(cr, uid, domain, context=context)
        try:
            offset = 0
            while True:
                #search for the n first terms to translate
                term_ids = all_term_ids[offset:offset + limit]
                if term_ids:
                    offset += limit
                    self._send_translation_terms(cr, uid, term_ids, context=context)
                    _logger.info("%s Translation terms have been posted to Gengo successfully", len(term_ids))
                if not len(term_ids) == limit:
                    break
        except Exception, e:
            _logger.error("%s", e)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
