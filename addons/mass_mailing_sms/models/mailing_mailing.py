# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.osv import expression

_logger = logging.getLogger(__name__)


class Mailing(models.Model):
    _inherit = 'mailing.mailing'

    @api.model
    def default_get(self, fields):
        res = super(Mailing, self).default_get(fields)
        if fields is not None and 'keep_archives' in fields and res.get('mailing_type') == 'sms':
            res['keep_archives'] = True
        return res

    # mailing options
    mailing_type = fields.Selection(selection_add=[
        ('sms', 'SMS')
    ], ondelete={'sms': 'set default'})

    # 'sms_subject' added to override 'subject' field (string attribute should be labelled "Title" when mailing_type == 'sms').
    # 'sms_subject' should have the same helper as 'subject' field when 'mass_mailing_sms' installed.
    # otherwise 'sms_subject' will get the old helper from 'mass_mailing' module.
    # overriding 'subject' field helper in this model is not working, since the helper will keep the new value
    # even when 'mass_mailing_sms' removed (see 'mailing_mailing_view_form_sms' for more details).                    
    sms_subject = fields.Char(
        'Title', related='subject',
        readonly=False, translate=False,
        help='For an email, the subject your recipients will see in their inbox.\n'
             'For an SMS, the internal title of the message.')
    # sms options
    body_plaintext = fields.Text(
        'SMS Body', compute='_compute_body_plaintext',
        store=True, readonly=False)
    sms_template_id = fields.Many2one('sms.template', string='SMS Template', ondelete='set null')
    sms_has_insufficient_credit = fields.Boolean(
        'Insufficient IAP credits', compute='_compute_sms_has_iap_failure') # used to propose buying IAP credits
    sms_has_unregistered_account = fields.Boolean(
        'Unregistered IAP account', compute='_compute_sms_has_iap_failure') # used to propose to Register the SMS IAP account
    sms_force_send = fields.Boolean(
        'Send Directly', help='Immediately send the SMS Mailing instead of queuing up. Use at your own risk.')
    # opt_out_link
    sms_allow_unsubscribe = fields.Boolean('Include opt-out link', default=False)
    # A/B Testing
    ab_testing_sms_winner_selection = fields.Selection(
        related="campaign_id.ab_testing_sms_winner_selection",
        default="clicks_ratio", readonly=False, copy=True)
    ab_testing_mailings_sms_count = fields.Integer(related="campaign_id.ab_testing_mailings_sms_count")

    @api.depends('mailing_type')
    def _compute_medium_id(self):
        super(Mailing, self)._compute_medium_id()
        for mailing in self:
            if mailing.mailing_type == 'sms' and (not mailing.medium_id or mailing.medium_id == self.env.ref('utm.utm_medium_email')):
                mailing.medium_id = self.env.ref('mass_mailing_sms.utm_medium_sms').id
            elif mailing.mailing_type == 'mail' and (not mailing.medium_id or mailing.medium_id == self.env.ref('mass_mailing_sms.utm_medium_sms')):
                mailing.medium_id = self.env.ref('utm.utm_medium_email').id

    @api.depends('sms_template_id', 'mailing_type')
    def _compute_body_plaintext(self):
        for mailing in self:
            if mailing.mailing_type == 'sms' and mailing.sms_template_id:
                mailing.body_plaintext = mailing.sms_template_id.body

    @api.depends('mailing_trace_ids.failure_type')
    def _compute_sms_has_iap_failure(self):
        self.sms_has_insufficient_credit = self.sms_has_unregistered_account = False
        traces = self.env['mailing.trace'].sudo()._read_group([
                    ('mass_mailing_id', 'in', self.ids),
                    ('trace_type', '=', 'sms'),
                    ('failure_type', 'in', ['sms_acc', 'sms_credit'])
        ], ['mass_mailing_id', 'failure_type'])

        for mass_mailing, failure_type in traces:
            if failure_type == 'sms_credit':
                mass_mailing.sms_has_insufficient_credit = True
            elif failure_type == 'sms_acc':
                mass_mailing.sms_has_unregistered_account = True

    # --------------------------------------------------
    # ORM OVERRIDES
    # --------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Get subject from "sms_subject" field when SMS installed (used to
            # build the name of record in the super 'create' method)
            if vals.get('mailing_type') == 'sms' and vals.get('sms_subject'):
                vals['subject'] = vals['sms_subject']
        return super().create(vals_list)

    # --------------------------------------------------
    # BUSINESS / VIEWS ACTIONS
    # --------------------------------------------------

    def action_retry_failed(self):
        mass_sms = self.filtered(lambda m: m.mailing_type == 'sms')
        if mass_sms:
            mass_sms.action_retry_failed_sms()
        return super(Mailing, self - mass_sms).action_retry_failed()

    def action_retry_failed_sms(self):
        failed_sms = self.env['sms.sms'].sudo().search([
            ('mailing_id', 'in', self.ids),
            ('state', '=', 'error')
        ])
        failed_sms.mapped('mailing_trace_ids').unlink()
        failed_sms.unlink()
        self.action_put_in_queue()

    def action_test(self):
        if self.mailing_type == 'sms':
            ctx = dict(self.env.context, default_mailing_id=self.id, dialog_size='medium')
            return {
                'name': _('Test Mailing'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'mailing.sms.test',
                'target': 'new',
                'context': ctx,
            }
        return super(Mailing, self).action_test()

    def _action_view_traces_filtered(self, view_filter):
        action = super(Mailing, self)._action_view_traces_filtered(view_filter)
        if self.mailing_type == 'sms':
            action['views'] = [(self.env.ref('mass_mailing_sms.mailing_trace_view_tree_sms').id, 'tree'),
                               (self.env.ref('mass_mailing_sms.mailing_trace_view_form_sms').id, 'form')]
        return action

    def action_buy_sms_credits(self):
        url = self.env['iap.account'].get_credits_url(service_name='sms')
        return {
            'type': 'ir.actions.act_url',
            'url': url,
        }

    # --------------------------------------------------
    # SMS SEND
    # --------------------------------------------------

    def _get_opt_out_list_sms(self):
        """ Give list of opt-outed records, depending on specific model-based
        computation if available.

        :return list: opt-outed record IDs
        """
        self.ensure_one()
        opt_out = []
        target = self.env[self.mailing_model_real]
        if hasattr(self.env[self.mailing_model_name], '_mailing_get_opt_out_list_sms'):
            opt_out = self.env[self.mailing_model_name]._mailing_get_opt_out_list_sms(self)
            _logger.info("Mass SMS %s targets %s: optout: %s contacts", self, target._name, len(opt_out))
        else:
            _logger.info("Mass SMS %s targets %s: no opt out list available", self, target._name)
        return opt_out

    def _get_seen_list_sms(self):
        """Returns a set of emails already targeted by current mailing/campaign (no duplicates)"""
        self.ensure_one()
        target = self.env[self.mailing_model_real]

        partner_fields = []
        if isinstance(target, self.pool['mail.thread.phone']):
            phone_fields = ['phone_sanitized']
        else:
            phone_fields = [
                fname for fname in target._phone_get_number_fields()
                if fname in target._fields and target._fields[fname].store
            ]
            partner_fields = target._mail_get_partner_fields()
        partner_field = next(
            (fname for fname in partner_fields if target._fields[fname].store and target._fields[fname].type == 'many2one'),
            False
        )
        if not phone_fields and not partner_field:
            raise UserError(_("Unsupported %s for mass SMS", self.mailing_model_id.name))

        query = """
            SELECT %(select_query)s
              FROM mailing_trace trace
              JOIN %(target_table)s target ON (trace.res_id = target.id)
              %(join_add_query)s
             WHERE (%(where_query)s)
               AND trace.mass_mailing_id = %%(mailing_id)s
               AND trace.model = %%(target_model)s
        """
        if phone_fields:
            # phone fields are checked on target mailed model
            select_query = 'target.id, ' + ', '.join('target.%s' % fname for fname in phone_fields)
            where_query = ' OR '.join('target.%s IS NOT NULL' % fname for fname in phone_fields)
            join_add_query = ''
        else:
            # phone fields are checked on res.partner model
            partner_phone_fields = ['mobile', 'phone']
            select_query = 'target.id, ' + ', '.join('partner.%s' % fname for fname in partner_phone_fields)
            where_query = ' OR '.join('partner.%s IS NOT NULL' % fname for fname in partner_phone_fields)
            join_add_query = 'JOIN res_partner partner ON (target.%s = partner.id)' % partner_field

        query = query % {
            'select_query': select_query,
            'where_query': where_query,
            'target_table': target._table,
            'join_add_query': join_add_query,
        }
        params = {'mailing_id': self.id, 'target_model': self.mailing_model_real}
        self._cr.execute(query, params)
        query_res = self._cr.fetchall()
        seen_list = set(number for item in query_res for number in item[1:] if number)
        seen_ids = set(item[0] for item in query_res)
        _logger.info("Mass SMS %s targets %s: already reached %s SMS", self, target._name, len(seen_list))
        return list(seen_ids), list(seen_list)

    def _send_sms_get_composer_values(self, res_ids):
        return {
            # content
            'body': self.body_plaintext,
            'template_id': self.sms_template_id.id,
            'res_model': self.mailing_model_real,
            'res_ids': repr(res_ids),
            # options
            'composition_mode': 'mass',
            'mailing_id': self.id,
            'mass_keep_log': self.keep_archives,
            'mass_force_send': self.sms_force_send,
            'mass_sms_allow_unsubscribe': self.sms_allow_unsubscribe,
        }

    def action_send_mail(self, res_ids=None):
        mass_sms = self.filtered(lambda m: m.mailing_type == 'sms')
        if mass_sms:
            mass_sms.action_send_sms(res_ids=res_ids)
        return super(Mailing, self - mass_sms).action_send_mail(res_ids=res_ids)

    def action_send_sms(self, res_ids=None):
        for mailing in self:
            if not res_ids:
                res_ids = mailing._get_remaining_recipients()
            if res_ids:
                composer = self.env['sms.composer'].with_context(active_id=False).create(mailing._send_sms_get_composer_values(res_ids))
                composer._action_send_sms()
        return True

    # ------------------------------------------------------
    # STATISTICS
    # ------------------------------------------------------

    def _prepare_statistics_email_values(self):
        """Return some statistics that will be displayed in the mailing statistics email.

        Each item in the returned list will be displayed as a table, with a title and
        1, 2 or 3 columns.
        """
        values = super(Mailing, self)._prepare_statistics_email_values()
        if self.mailing_type == 'sms':
            mailing_type = self._get_pretty_mailing_type()
            values['title'] = _('24H Stats of %(mailing_type)s "%(mailing_name)s"',
                                mailing_type=mailing_type,
                                mailing_name=self.subject
                               )
            values['kpi_data'][0] = {
                'kpi_fullname': _('Report for %(expected)i %(mailing_type)s Sent',
                                  expected=self.expected,
                                  mailing_type=mailing_type
                                 ),
                'kpi_col1': {
                    'value': f'{self.received_ratio}%',
                    'col_subtitle': _('RECEIVED (%i)', self.delivered),
                },
                'kpi_col2': {
                    'value': f'{self.clicks_ratio}%',
                    'col_subtitle': _('CLICKED (%i)', self.clicked),
                },
                'kpi_col3': {
                    'value': f'{self.bounced_ratio}%',
                    'col_subtitle': _('BOUNCED (%i)', self.bounced),
                },
                'kpi_action': None,
                'kpi_name': self.mailing_type,
            }
        return values

    def _get_pretty_mailing_type(self):
        if self.mailing_type == 'sms':
            return _('SMS Text Message')
        return super(Mailing, self)._get_pretty_mailing_type()

    # --------------------------------------------------
    # TOOLS
    # --------------------------------------------------

    def _get_default_mailing_domain(self):
        mailing_domain = super(Mailing, self)._get_default_mailing_domain()
        if self.mailing_type == 'sms' and 'phone_sanitized_blacklisted' in self.env[self.mailing_model_name]._fields:
            mailing_domain = expression.AND([mailing_domain, [('phone_sanitized_blacklisted', '=', False)]])

        return mailing_domain

    def convert_links(self):
        sms_mailings = self.filtered(lambda m: m.mailing_type == 'sms')
        res = {}
        for mailing in sms_mailings:
            tracker_values = mailing._get_link_tracker_values()
            body = mailing._shorten_links_text(mailing.body_plaintext, tracker_values)
            res[mailing.id] = body
        res.update(super(Mailing, self - sms_mailings).convert_links())
        return res

    # ------------------------------------------------------
    # A/B Test Override
    # ------------------------------------------------------

    def _get_ab_testing_description_modifying_fields(self):
        fields_list = super()._get_ab_testing_description_modifying_fields()
        return fields_list + ['ab_testing_sms_winner_selection']

    def _get_ab_testing_description_values(self):
        values = super()._get_ab_testing_description_values()
        if self.mailing_type == 'sms':
            values.update({
                'ab_testing_count': self.ab_testing_mailings_sms_count,
                'ab_testing_winner_selection': self.ab_testing_sms_winner_selection,
            })
        return values

    def _get_ab_testing_winner_selection(self):
        result = super()._get_ab_testing_winner_selection()
        if self.mailing_type == 'sms':
            ab_testing_winner_selection_description = dict(
                self._fields.get('ab_testing_sms_winner_selection').related_field.selection
            ).get(self.ab_testing_sms_winner_selection)
            result.update({
                'value': self.campaign_id.ab_testing_sms_winner_selection,
                'description': ab_testing_winner_selection_description
            })
        return result

    def _get_ab_testing_siblings_mailings(self):
        mailings = super()._get_ab_testing_siblings_mailings()
        if self.mailing_type == 'sms':
            mailings = self.campaign_id.mailing_sms_ids.filtered('ab_testing_enabled')
        return mailings

    def _get_default_ab_testing_campaign_values(self, values=None):
        campaign_values = super()._get_default_ab_testing_campaign_values(values)
        values = values or dict()
        if self.mailing_type == 'sms':
            sms_subject = values.get('sms_subject') or self.sms_subject
            if sms_subject:
                campaign_values['name'] = _("A/B Test: %s", sms_subject)
            campaign_values['ab_testing_sms_winner_selection'] = self.ab_testing_sms_winner_selection
        return campaign_values
