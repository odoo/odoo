# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import re
import time
import uuid

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

try:
    from gengo import Gengo
except ImportError:
    _logger.warning('Gengo library not found, Gengo features disabled. If you plan to use it, please install the gengo library from http://pypi.python.org/pypi/gengo')

GENGO_DEFAULT_LIMIT = 20


class BaseGengoTranslations(models.TransientModel):
    GENGO_KEY = "Gengo.UUID"
    GROUPS = ['base.group_system']

    _name = 'base.gengo.translations'

    @api.model
    def default_get(self, fields):
        res = super(BaseGengoTranslations, self).default_get(fields)
        res['authorized_credentials'], gengo = self.gengo_authentication()
        if 'lang_id' in fields:
            res['lang_id'] = self.env['res.lang'].search([
                ('code', '=', self.env.context.get('lang', 'en_US'))
            ], limit=1).id
        return res

    sync_type = fields.Selection([
        ('send', 'Send New Terms'),
        ('receive', 'Receive Translation'),
        ('both', 'Both')
        ], "Sync Type", default='both', required=True)
    lang_id = fields.Many2one('res.lang', 'Language', required=True)
    sync_limit = fields.Integer("No. of terms to sync", default=20)
    authorized_credentials = fields.Boolean('The private and public keys are valid')

    @api.model_cr
    def init(self):
        icp = self.env['ir.config_parameter'].sudo()
        if not icp.get_param(self.GENGO_KEY, default=None):
            icp.set_param(self.GENGO_KEY, str(uuid.uuid4()), groups=self.GROUPS)

    @api.model_cr
    def get_gengo_key(self):
        icp = self.env['ir.config_parameter'].sudo()
        return icp.get_param(self.GENGO_KEY, default="Undefined")

    @api.multi
    def open_company(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'res.company',
            'res_id': self.env.user.company_id.id,
            'target': 'current',
            }

    @api.model
    def gengo_authentication(self):
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
        user = self.env.user
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

    @api.multi
    def act_update(self):
        '''
        Function called by the wizard.
        '''
        flag, gengo = self.gengo_authentication()
        if not flag:
            raise UserError(gengo)
        for wizard in self:
            supported_langs = self.env['ir.translation']._get_all_supported_languages()
            language = self.env['ir.translation']._get_gengo_corresponding_language(wizard.lang_id.code)
            if language not in supported_langs:
                raise UserError(_('This language is not supported by the Gengo translation services.'))

            ctx = self.env.context.copy()
            ctx['gengo_language'] = wizard.lang_id.id
            if wizard.sync_limit > 200 or wizard.sync_limit < 1:
                raise UserError(_('The number of terms to sync should be between 1 to 200 to work with Gengo translation services.'))
            if wizard.sync_type in ['send', 'both']:
                self.with_context(ctx)._sync_request(wizard.sync_limit)
            if wizard.sync_type in ['receive', 'both']:
                self.with_context(ctx)._sync_response(wizard.sync_limit)
        return {'type': 'ir.actions.act_window_close'}

    @api.model
    def _sync_response(self, limit=GENGO_DEFAULT_LIMIT):
        """
        This method will be called by cron services to get translations from
        Gengo. It will read translated terms and comments from Gengo and will
        update respective ir.translation in Odoo.
        """
        IrTranslation = self.env['ir.translation']
        flag, gengo = self.gengo_authentication()
        if not flag:
            _logger.warning("%s", gengo)
        else:
            offset = 0
            all_translation_ids = IrTranslation.search([
                ('state', '=', 'inprogress'),
                ('gengo_translation', 'in', ('machine', 'standard', 'pro', 'ultra')),
                ('order_id', "!=", False)])
            while True:
                translation_ids = all_translation_ids[offset:offset + limit]
                offset += limit
                if not translation_ids:
                    break

                terms_progress = {
                    'gengo_order_ids': set(),
                    'ir_translation_ids': set(),
                }
                for term in translation_ids:
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
                                self._update_terms_job(job)
        return True

    @api.model
    def _update_terms_job(self, job):
        translation = self.env['ir.translation'].browse(int(job['custom_data']))
        vals = {}
        if job.get('status', False) in ('queued', 'available', 'pending', 'reviewable'):
            vals['state'] = 'inprogress'
        if job.get('body_tgt', False) and job.get('status', False) == 'approved':
            vals['value'] = job['body_tgt']
        if job.get('status', False) in ('approved', 'canceled'):
            vals['state'] = 'translated'
        if vals:
            try:
                translation.write(vals)
            except ValidationError:
                pass

    @api.model
    def _update_terms(self, response, term_ids):
        """
        Update the terms after their translation were requested to Gengo
        """
        vals = {
            'order_id': response.get('order_id', ''),
            'state': 'inprogress'
        }
        term_ids.write(vals)
        jobs = response.get('jobs', [])
        if jobs:
            for t_id, job in jobs.items():
                self._update_terms_job(job)

        return

    @api.model
    def pack_jobs_request(self, term_ids, context=None):
        ''' prepare the terms that will be requested to gengo and returns them in a dictionary with following format
            {'jobs': {
                'term1.id': {...}
                'term2.id': {...}
                }
            }'''
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        IrTranslation = self.env['ir.translation']
        jobs = {}
        user = self.env.user
        auto_approve = 1 if user.company_id.gengo_auto_approve else 0
        for term in term_ids:
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
                    'lc_tgt': IrTranslation._get_gengo_corresponding_language(term.lang),
                    'auto_approve': auto_approve,
                    'comment': comment,
                    'callback_url': "%s/website/gengo_callback?pgk=%s&db=%s" % (base_url, self.get_gengo_key(), self.env.cr.dbname)
                }
        return {'jobs': jobs, 'as_group': 0}

    @api.model
    def _send_translation_terms(self, term_ids):
        """
        Send a request to Gengo with all the term_ids in a different job, get the response and update the terms in
        database accordingly.
        """
        flag, gengo = self.gengo_authentication()
        if flag:
            request = self.pack_jobs_request(term_ids)
            if request['jobs']:
                result = gengo.postTranslationJobs(jobs=request)
                if result['opstat'] == 'ok':
                    self._update_terms(result['response'], term_ids)
        else:
            _logger.error(gengo)
        return True

    @api.model
    def _sync_request(self, limit=GENGO_DEFAULT_LIMIT):
        """
        This scheduler will send a job request to the gengo , which terms are
        waiing to be translated and for which gengo_translation is enabled.

        A special key 'gengo_language' can be passed in the context in order to
        request only translations of that language only. Its value is the language
        ID in Odoo.
        """
        domain = [
            ('state', '=', 'to_translate'),
            ('gengo_translation', 'in', ('machine', 'standard', 'pro', 'ultra')),
            ('order_id', "=", False)]
        if self.env.context.get('gengo_language', False):
            lc = self.env['res.lang'].browse(self.env.context['gengo_language']).code
            domain.append(('lang', '=', lc))

        all_term_ids = self.env['ir.translation'].search(domain)
        try:
            offset = 0
            while True:
                #search for the n first terms to translate
                term_ids = all_term_ids[offset:offset + limit]
                if term_ids:
                    offset += limit
                    self._send_translation_terms(term_ids)
                    _logger.info("%s Translation terms have been posted to Gengo successfully", len(term_ids))
                if not len(term_ids) == limit:
                    break
        except Exception, e:
            _logger.error("%s", e)
