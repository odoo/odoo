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

import logging
import re
import time

from openerp.osv import osv, fields
from openerp import tools
from openerp.tools.translate import _

_logger = logging.getLogger(__name__)

try:
    from mygengo import MyGengo
except ImportError:
    _logger.warning('Gengo library not found, Gengo features disabled. If you plan to use it, please install the mygengo library from http://pypi.python.org/pypi/mygengo')
    class MyGengo(object):
        def __init__(self, *args, **kwargs):
            # no context for translations - so don't bother
            raise ImportError('Gengo library not found, please install mygengo from http://pypi.python.org/pypi/mygengo')

GENGO_DEFAULT_LIMIT = 20

class base_gengo_translations(osv.osv_memory):

    _name = 'base.gengo.translations'
    _columns = {
        'sync_type': fields.selection([('send', 'Send New Terms'),
                                       ('receive', 'Receive Translation'),
                                       ('both', 'Both')], "Sync Type"),
        'lang_id': fields.many2one('res.lang', 'Language', required=True),
        'sync_limit': fields.integer("No. of terms to sync"),
    }
    _defaults = {'sync_type' : 'both',
                 'sync_limit' : 20
         }
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
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        if not user.company_id.gengo_public_key or not user.company_id.gengo_private_key:
            return (False, _("Gengo `Public Key` or `Private Key` are missing. Enter your Gengo authentication parameters under `Settings > Companies > Gengo Parameters`."))
        try:
            gengo = MyGengo(
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
        update respective ir.translation in openerp.
        """
        translation_pool = self.pool.get('ir.translation')
        flag, gengo = self.gengo_authentication(cr, uid, context=context)
        if not flag:
            _logger.warning("%s", gengo)
        else:
            offset = 0
            all_translation_ids = translation_pool.search(cr, uid, [('state', '=', 'inprogress'), ('gengo_translation', 'in', ('machine', 'standard', 'pro', 'ultra')), ('job_id', "!=", False)], context=context)
            while True:
                translation_ids = all_translation_ids[offset:offset + limit]
                if translation_ids:
                    offset += limit
                    translation_terms = translation_pool.browse(cr, uid, translation_ids, context=context)
                    gengo_job_id = [term.job_id for term in translation_terms]
                    if gengo_job_id:
                        gengo_ids = ','.join(gengo_job_id)
                        job_response = gengo.getTranslationJobBatch(id=gengo_ids)
                        if job_response['opstat'] == 'ok':
                            job_response_dict = dict([(job['job_id'], job) for job in job_response['response']['jobs']])
                            for term in translation_terms:
                                up_term = up_comment = 0
                                vals = {}
                                if job_response_dict[term.job_id]['status'] == 'approved':
                                    vals.update({'state': 'translated',
                                        'value': job_response_dict[term.job_id]['body_tgt']})
                                    up_term += 1
                                job_comment = gengo.getTranslationJobComments(id=term.job_id)
                                if job_comment['opstat'] == 'ok':
                                    gengo_comments = ""
                                    for comment in job_comment['response']['thread']:
                                        gengo_comments += _('%s\n-- Commented on %s by %s.\n\n') % (comment['body'], time.ctime(comment['ctime']), comment['author'])
                                    vals.update({'gengo_comment': gengo_comments})
                                    up_comment += 1
                                if vals:
                                    translation_pool.write(cr, uid, term.id, vals)
                                _logger.info("Successfully Updated `%d` terms and %d Comments." % (up_term, up_comment))
                if not len(translation_ids) == limit:
                    break
        return True

    def _update_terms(self, cr, uid, response, context=None):
        """
        Update the terms after their translation were requested to Gengo
        """
        translation_pool = self.pool.get('ir.translation')
        for jobs in response['jobs']:
            for t_id, res in jobs.items():
                vals = {}
                t_id = int(t_id)
                tier = translation_pool.read(cr, uid, [t_id], ['gengo_translation'], context=context)[0]['gengo_translation']
                if tier == "machine":
                    vals.update({'value': res['body_tgt'], 'state': 'translated'})
                else:
                    vals.update({'job_id': res['job_id'], 'state': 'inprogress'})
                translation_pool.write(cr, uid, [t_id], vals, context=context)
        return

    def pack_jobs_request(self, cr, uid, term_ids, context=None):
        ''' prepare the terms that will be requested to gengo and returns them in a dictionary with following format
            {'jobs': {
                'term1.id': {...}
                'term2.id': {...}
                }
            }'''

        translation_pool = self.pool.get('ir.translation')
        jobs = {}
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        auto_approve = 1 if user.company_id.gengo_auto_approve else 0
        for term in translation_pool.browse(cr, uid, term_ids, context=context):
            if re.search(r"\w", term.src or ""):
                jobs[term.id] = {'type': 'text',
                        'slug': 'single::English to ' + term.lang,
                        'tier': tools.ustr(term.gengo_translation),
                        'body_src': term.src,
                        'lc_src': 'en',
                        'lc_tgt': translation_pool._get_gengo_corresponding_language(term.lang),
                        'auto_approve': auto_approve,
                        'comment': user.company_id.gengo_comment and "%s %s"%(user.company_id.gengo_comment,term.gengo_comment) or term.gengo_comment, 
                        'callback_url': self.pool.get('ir.config_parameter').get_param(cr, uid,'web.base.url') + '/website/gengo_callback/' + str(term.id)
                }
        return {'jobs': jobs}


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
                    self._update_terms(cr, uid, result['response'], context=context)
        else:
            _logger.error(gengo)
        return True

    def _sync_request(self, cr, uid, limit=GENGO_DEFAULT_LIMIT, context=None):
        """
        This scheduler will send a job request to the gengo , which terms are
        waiing to be translated and for which gengo_translation is enabled. 

        A special key 'gengo_language' can be passed in the context in order to 
        request only translations of that language only. Its value is the language 
        ID in openerp.
        """
        if context is None:
            context = {}
        language_pool = self.pool.get('res.lang')
        translation_pool = self.pool.get('ir.translation')
        try:
            #by default, the request will be made for all terms that needs it, whatever the language
            lang_ids = language_pool.search(cr, uid, [], context=context)
            if context.get('gengo_language'):
                #but if this specific key is given, then we restrict the request on terms of this language only
                lang_ids = [context.get('gengo_language')]
            langs = [lang.code for lang in language_pool.browse(cr, uid, lang_ids, context=context)]
            offset = 0
            all_term_ids = translation_pool.search(cr, uid, [('state', '=', 'to_translate'), ('gengo_translation', 'in', ('machine', 'standard', 'pro', 'ultra')), ('lang', 'in', langs), ('job_id', "=", False)], context=context)
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
