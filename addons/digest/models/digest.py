# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import math
import pytz

from datetime import datetime, date
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, tools
from odoo.addons.base.models.ir_mail_server import MailDeliveryException
from odoo.exceptions import AccessError
from odoo.tools.float_utils import float_round

_logger = logging.getLogger(__name__)


class Digest(models.Model):
    _name = 'digest.digest'
    _description = 'Digest'

    # Digest description
    name = fields.Char(string='Name', required=True, translate=True)
    user_ids = fields.Many2many('res.users', string='Recipients', domain="[('share', '=', False)]")
    periodicity = fields.Selection([('weekly', 'Weekly'),
                                    ('monthly', 'Monthly'),
                                    ('quarterly', 'Quarterly')],
                                   string='Periodicity', default='weekly', required=True)
    next_run_date = fields.Date(string='Next Send Date')
    template_id = fields.Many2one('mail.template', string='Email Template',
                                  domain="[('model','=','digest.digest')]",
                                  default=lambda self: self.env.ref('digest.digest_mail_template'),
                                  required=True)
    currency_id = fields.Many2one(related="company_id.currency_id", string='Currency', readonly=False)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company.id)
    available_fields = fields.Char(compute='_compute_available_fields')
    is_subscribed = fields.Boolean('Is user subscribed', compute='_compute_is_subscribed')
    state = fields.Selection([('activated', 'Activated'), ('deactivated', 'Deactivated')], string='Status', readonly=True, default='activated')
    # First base-related KPIs
    kpi_res_users_connected = fields.Boolean('Connected Users')
    kpi_res_users_connected_value = fields.Integer(compute='_compute_kpi_res_users_connected_value')
    kpi_mail_message_total = fields.Boolean('Messages')
    kpi_mail_message_total_value = fields.Integer(compute='_compute_kpi_mail_message_total_value')

    def _compute_is_subscribed(self):
        for digest in self:
            digest.is_subscribed = self.env.user in digest.user_ids

    def _compute_available_fields(self):
        for digest in self:
            kpis_values_fields = []
            for field_name, field in digest._fields.items():
                if field.type == 'boolean' and field_name.startswith(('kpi_', 'x_kpi_', 'x_studio_kpi_')) and digest[field_name]:
                    kpis_values_fields += [field_name + '_value']
            digest.available_fields = ', '.join(kpis_values_fields)

    def _get_kpi_compute_parameters(self):
        return fields.Date.to_string(self._context.get('start_date')), fields.Date.to_string(self._context.get('end_date')), self._context.get('company')

    def _compute_kpi_res_users_connected_value(self):
        for record in self:
            start, end, company = record._get_kpi_compute_parameters()
            user_connected = self.env['res.users'].search_count([('company_id', '=', company.id), ('login_date', '>=', start), ('login_date', '<', end)])
            record.kpi_res_users_connected_value = user_connected

    def _compute_kpi_mail_message_total_value(self):
        discussion_subtype_id = self.env.ref('mail.mt_comment').id
        for record in self:
            start, end, company = record._get_kpi_compute_parameters()
            total_messages = self.env['mail.message'].search_count([('create_date', '>=', start), ('create_date', '<', end), ('subtype_id', '=', discussion_subtype_id), ('message_type', 'in', ['comment', 'email'])])
            record.kpi_mail_message_total_value = total_messages

    @api.onchange('periodicity')
    def _onchange_periodicity(self):
        self.next_run_date = self._get_next_run_date()

    @api.model
    def create(self, vals):
        vals['next_run_date'] = date.today() + relativedelta(days=3)
        return super(Digest, self).create(vals)

    def action_subscribe(self):
        if self.env.user not in self.user_ids:
            self.sudo().user_ids |= self.env.user

    def action_unsubcribe(self):
        if self.env.user in self.user_ids:
            self.sudo().user_ids -= self.env.user

    def action_activate(self):
        self.state = 'activated'

    def action_deactivate(self):
        self.state = 'deactivated'

    def action_send(self):
        for digest in self:
            for user in digest.user_ids:
                subject = '%s: %s' % (user.company_id.name, digest.name)
                digest.template_id.with_context(user=user).send_mail(digest.id, force_send=True, raise_exception=True, email_values={'email_to': user.email, 'subject': subject})
            digest.next_run_date = digest._get_next_run_date()

    def compute_kpis(self, company, user):
        self.ensure_one()
        res = {}
        for tf_name, tf in self._compute_timeframes(company).items():
            digest = self.with_context(start_date=tf[0][0], end_date=tf[0][1], company=company).with_user(user)
            previous_digest = self.with_context(start_date=tf[1][0], end_date=tf[1][1], company=company).with_user(user)
            kpis = {}
            for field_name, field in self._fields.items():
                if field.type == 'boolean' and field_name.startswith(('kpi_', 'x_kpi_', 'x_studio_kpi_')) and self[field_name]:

                    try:
                        compute_value = digest[field_name + '_value']
                        previous_value = previous_digest[field_name + '_value']
                    except AccessError:  # no access rights -> just skip that digest details from that user's digest email
                        continue
                    margin = self._get_margin_value(compute_value, previous_value)
                    if self._fields[field_name+'_value'].type == 'monetary':
                        converted_amount = self._format_human_readable_amount(compute_value)
                        kpis.update({field_name: {field_name: self._format_currency_amount(converted_amount, company.currency_id), 'margin': margin}})
                    else:
                        kpis.update({field_name: {field_name: compute_value, 'margin': margin}})

                res.update({tf_name: kpis})
        return res

    def compute_tips(self, company, user):
        tip = self.env['digest.tip'].search([('user_ids', '!=', user.id), '|', ('group_id', 'in', user.groups_id.ids), ('group_id', '=', False)], limit=1)
        if not tip:
            return False
        tip.user_ids += user
        body = tools.html_sanitize(tip.tip_description)
        tip_description = self.env['mail.template']._render_template(body, 'digest.tip', self.id)
        return tip_description

    def compute_kpis_actions(self, company, user):
        """ Give an optional action to display in digest email linked to some KPIs.

        :return dict: key: kpi name (field name), value: an action that will be
          concatenated with /web#action={action}
        """
        return {}

    def _get_next_run_date(self):
        self.ensure_one()
        if self.periodicity == 'weekly':
            delta = relativedelta(weeks=1)
        elif self.periodicity == 'monthly':
            delta = relativedelta(months=1)
        elif self.periodicity == 'quarterly':
            delta = relativedelta(months=3)
        return date.today() + delta

    def _compute_timeframes(self, company):
        now = datetime.utcnow()
        tz_name = company.resource_calendar_id.tz
        if tz_name:
            now = pytz.timezone(tz_name).localize(now)
        start_date = now.date()
        return {
            'yesterday': (
                (start_date + relativedelta(days=-1), start_date),
                (start_date + relativedelta(days=-2), start_date + relativedelta(days=-1))),
            'lastweek': (
                (start_date + relativedelta(weeks=-1), start_date),
                (start_date + relativedelta(weeks=-2), start_date + relativedelta(weeks=-1))),
            'lastmonth': (
                (start_date + relativedelta(months=-1), start_date),
                (start_date + relativedelta(months=-2), start_date + relativedelta(months=-1))),
        }

    def _get_margin_value(self, value, previous_value=0.0):
        margin = 0.0
        if (value != previous_value) and (value != 0.0 and previous_value != 0.0):
            margin = float_round((float(value-previous_value) / previous_value or 1) * 100, precision_digits=2)
        return margin

    def _format_currency_amount(self, amount, currency_id):
        pre = currency_id.position == 'before'
        symbol = u'{symbol}'.format(symbol=currency_id.symbol or '')
        return u'{pre}{0}{post}'.format(amount, pre=symbol if pre else '', post=symbol if not pre else '')

    def _format_human_readable_amount(self, amount, suffix=''):
        for unit in ['', 'K', 'M', 'G']:
            if abs(amount) < 1000.0:
                return "%3.2f%s%s" % (amount, unit, suffix)
            amount /= 1000.0
        return "%.2f%s%s" % (amount, 'T', suffix)

    @api.model
    def _cron_send_digest_email(self):
        digests = self.search([('next_run_date', '=', fields.Date.today()), ('state', '=', 'activated')])
        for digest in digests:
            try:
                digest.action_send()
            except MailDeliveryException as e:
                _logger.warning('MailDeliveryException while sending digest %d. Digest is now scheduled for next cron update.')
