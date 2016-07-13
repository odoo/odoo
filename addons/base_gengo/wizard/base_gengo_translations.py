# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import re
import time
import uuid

from odoo import api, fields, models, SUPERUSER_ID, tools, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

try:
    from gengo import Gengo
except ImportError:
    _logger.warning('Gengo library not found, Gengo features disabled. If you plan to use it, please install the gengo library from http://pypi.python.org/pypi/gengo')

GENGO_DEFAULT_LIMIT = 20


class BaseGengoTranslations(models.TransientModel):
    _name = 'base.gengo.translations'

    GENGO_KEY = "Gengo.UUID"
    GROUPS = ['base.group_system']

    sync_type = fields.Selection([('send', 'Send New Terms'),
                                  ('receive', 'Receive Translation'),
                                  ('both', 'Both')], string="Sync Type", default='both', required=True)
    lang_id = fields.Many2one('res.lang', string='Language', required=True)
    sync_limit = fields.Integer(string="No. of terms to sync", default=20)
    authorized_credentials = fields.Boolean('The private and public keys are valid')

    def init(self, cr):
        env = api.Environment(cr, SUPERUSER_ID, {})
        IrConfigParam = env['ir.config_parameter']
        if not IrConfigParam.get_param(self.GENGO_KEY, default=None):
            IrConfigParam.set_param(self.GENGO_KEY, str(uuid.uuid4()), groups=self.GROUPS)

    @api.model
    def default_get(self, fields):
        res = super(BaseGengoTranslations, self).default_get(fields)
        res['authorized_credentials'], gengo = self.gengo_authentication()
        if 'lang_id' in fields:
            res['lang_id'] = self.env['res.lang'].search([('code', '=', self.env.context.get('lang', 'en_US'))], limit=1)
        return res

    @api.model
    def get_gengo_key(self):
        return self.env['ir.config_parameter'].get_param(self.GENGO_KEY)

    @api.multi
    def open_company(self):
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
        IrTranslation = self.env['ir.translation']
        if not flag:
            raise UserError(gengo)
        supported_langs = IrTranslation._get_all_supported_languages()
        for gengo_translation in self:
            language = IrTranslation._get_gengo_corresponding_language(gengo_translation.lang_id.code)
            if language not in supported_langs:
                raise UserError(_('This language is not supported by the Gengo translation services.'))

            if gengo_translation.sync_limit > 200 or gengo_translation.sync_limit < 1:
                raise UserError(_('The number of terms to sync should be between 1 to 200 to work with Gengo translation services.'))
            if gengo_translation.sync_type in ['send', 'both']:
                self.with_context(gengo_language=gengo_translation.lang_id.id)._sync_request(gengo_translation.sync_limit)
            if gengo_translation.sync_type in ['receive', 'both']:
                self.with_context(gengo_language=gengo_translation.lang_id.id)._sync_response(gengo_translation.sync_limit)
        return {'type': 'ir.actions.act_window_close'}

    @api.model
    def _sync_response(self, limit=GENGO_DEFAULT_LIMIT):
        """
        This method will be called by cron services to get translations from
        Gengo. It will read translated terms and comments from Gengo and will
        update respective ir.translation in Odoo.
        """
        flag, gengo = self.gengo_authentication()
        if not flag:
            _logger.warning("%s", gengo)
        else:
            offset = 0
            ir_translations = self.env['ir.translation'].search([('state', '=', 'inprogress'),
                                                                 ('gengo_translation', 'in', ('machine', 'standard', 'pro', 'ultra')),
                                                                 ('order_id', '!=', False)])

            while True:
                translations = ir_translations[offset:offset + limit]
                if not translations:
                    break
                offset += limit
                gengo_ids = None
                for order_id in translations.filtered('order_id').mapped('order_id'):
                    try:
                        order_response = gengo.getTranslationOrderJobs(id=order_id)
                    except Exception, e:
                        # Unauthorized Order Access, if order_id not found
                        _logger.error("%s", e)
                        continue
                    jobs_approved = order_response.get('response', []).get('order', []).get('jobs_approved', [])
                    gengo_ids = ','.join(jobs_approved)

                # Need to check, because getTranslationJobBatch don't catch this case and so call the getTranslationJobs because no ids in url
                if gengo_ids:
                    try:
                        job_response = gengo.getTranslationJobBatch(id=gengo_ids)
                    except:
                        continue
                    if job_response['opstat'] == 'ok':
                        for job in job_response['response'].get('jobs', []):
                            if job.get('custom_data') in map(str, translations.ids):
                                self._update_terms_job(job)
        return True

    def _update_terms_job(self, job):
        vals = {}
        if job.get('status') in ('queued', 'available', 'pending', 'reviewable'):
            vals['state'] = 'inprogress'
        elif job.get('status') in ('approved', 'canceled'):
            vals['state'] = 'translated'
            if job.get('body_tgt') and job['status'] == 'approved':
                vals['value'] = job['body_tgt']

        if vals:
            self.env['ir.translation'].browse(int(job['custom_data'])).write(vals)

    def _update_terms(self, response, translations):
        """
        Update the terms after their translation were requested to Gengo
        """
        translations.write({
            'order_id': response.get('order_id', ''),
            'state': 'inprogress'
        })
        jobs = response.get('jobs', {})
        for t_id, res in jobs.items():
            self._update_terms_job(res)
        return True

    def pack_jobs_request(self, translations):
        ''' prepare the terms that will be requested to gengo and returns them in a dictionary with following format
            {'jobs': {
                'term1.id': {...}
                'term2.id': {...}
                }
            }'''
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        jobs = {}
        company = self.env.user.company_id
        dbname = self.env.cr.dbname
        gengo_key = self.get_gengo_key()
        for term in translations:
            if re.search(r"\w", term.src or ""):
                comment = company.gengo_comment or ''
                if term.gengo_comment:
                    comment += '\n' + term.gengo_comment
                jobs[time.strftime('%Y%m%d%H%M%S') + '-' + str(term.id)] = {
                    'type': 'text',
                    'slug': 'Single :: English to ' + term.lang,
                    'tier': tools.ustr(term.gengo_translation),
                    'custom_data': str(term.id),
                    'body_src': term.src,
                    'lc_src': 'en',
                    'lc_tgt': term._get_gengo_corresponding_language(term.lang),
                    'auto_approve': 1 if company.gengo_auto_approve else 0,
                    'comment': comment,
                    'callback_url': "%s/website/gengo_callback?pgk=%s&db=%s" % (base_url, gengo_key, dbname)
                }
        return {'jobs': jobs, 'as_group': 0}

    def _send_translation_terms(self, translations):
        """
        Send a request to Gengo with all the translations in a different job, get the response and update the terms in
        database accordingly.
        """
        flag, gengo = self.gengo_authentication()
        if flag:
            request = self.pack_jobs_request(translations)
            if request['jobs']:
                result = gengo.postTranslationJobs(jobs=request)
                if result['opstat'] == 'ok':
                    self._update_terms(result['response'], translations)
        else:
            _logger.error(gengo)
        return True

    @api.model
    def _sync_request(self, limit=GENGO_DEFAULT_LIMIT):
        """
        This scheduler will send a job request to the gengo, which terms are
        waiting to be translated and for which gengo_translation is enabled.

        A special key 'gengo_language' can be passed in the context in order to
        request only translations of that language only. Its value is the language
        ID in Odoo.
        """
        domain = [('state', '=', 'to_translate'), ('gengo_translation', 'in', ('machine', 'standard', 'pro', 'ultra')), ('order_id', "=", False)]
        if self.env.context.get('gengo_language'):
            domain.append(('lang', '=', self.env['res.lang'].browse(self.env.context['gengo_language']).code))

        ir_translations = self.env['ir.translation'].search(domain)
        offset = 0
        try:
            while True:
                #search for the n first terms to translate
                translations = ir_translations[offset:offset + limit]
                if translations:
                    offset += limit
                    self._send_translation_terms(translations)
                    _logger.info("%s Translation terms have been posted to Gengo successfully", len(translations))
                if len(translations) != limit:
                    break
        except Exception, e:
            _logger.error("%s", e)
