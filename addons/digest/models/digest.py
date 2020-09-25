# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pytz

from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from werkzeug.urls import url_join

from odoo import api, fields, models, tools, _
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
    periodicity = fields.Selection([('daily', 'Daily'),
                                    ('weekly', 'Weekly'),
                                    ('monthly', 'Monthly'),
                                    ('quarterly', 'Quarterly')],
                                   string='Periodicity', default='daily', required=True)
    next_run_date = fields.Date(string='Next Send Date')
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
        return fields.Date.to_string(self._context.get('start_date')), fields.Date.to_string(self._context.get('end_date')), self.env.company

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
        digest = super(Digest, self).create(vals)
        if not digest.next_run_date:
             digest.next_run_date = digest._get_next_run_date()
        return digest

    # ------------------------------------------------------------
    # ACTIONS
    # ------------------------------------------------------------

    def action_subscribe(self):
        if self.env.user.has_group('base.group_user') and self.env.user not in self.user_ids:
            self.sudo().user_ids |= self.env.user

    def action_unsubcribe(self):
        if self.env.user.has_group('base.group_user') and self.env.user in self.user_ids:
            self.sudo().user_ids -= self.env.user

    def action_activate(self):
        self.state = 'activated'

    def action_deactivate(self):
        self.state = 'deactivated'

    def action_set_periodicity(self, periodicity):
        self.periodicity = periodicity

    def action_send(self):
        to_slowdown = self._check_daily_logs()
        for digest in self:
            for user in digest.user_ids:
                digest.with_context(
                    digest_slowdown=digest in to_slowdown,
                    lang=user.lang
                )._action_send_to_user(user, tips_count=1)
            if digest in to_slowdown:
                digest.write({'periodicity': 'weekly'})
            digest.next_run_date = digest._get_next_run_date()

    def _action_send_to_user(self, user, tips_count=1, consum_tips=True):
        web_base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')

        rendered_body = self.env['mail.render.mixin']._render_template(
            'digest.digest_mail_main',
            'digest.digest',
            self.ids,
            engine='qweb',
            add_context={
                'title': self.name,
                'top_button_label': _('Connect'),
                'top_button_url': url_join(web_base_url, '/web/login'),
                'company': user.company_id,
                'user': user,
                'tips_count': tips_count,
                'formatted_date': datetime.today().strftime('%B %d, %Y'),
                'display_mobile_banner': True,
                'kpi_data': self.compute_kpis(user.company_id, user),
                'tips': self.compute_tips(user.company_id, user, tips_count=tips_count, consumed=consum_tips),
                'preferences': self.compute_preferences(user.company_id, user),
            },
            post_process=True
        )[self.id]
        full_mail = self.env['mail.render.mixin']._render_encapsulate(
            'digest.digest_mail_layout',
            rendered_body,
            add_context={
                'company': user.company_id,
                'user': user,
            },
        )
        # create a mail_mail based on values, without attachments
        mail_values = {
            'subject': '%s: %s' % (user.company_id.name, self.name),
            'email_from': self.company_id.partner_id.email_formatted if self.company_id else self.env.user.email_formatted,
            'email_to': user.email_formatted,
            'body_html': full_mail,
            'auto_delete': True,
        }
        mail = self.env['mail.mail'].sudo().create(mail_values)
        mail.send(raise_exception=False)
        return True

    @api.model
    def _cron_send_digest_email(self):
        digests = self.search([('next_run_date', '<=', fields.Date.today()), ('state', '=', 'activated')])
        for digest in digests:
            try:
                digest.action_send()
            except MailDeliveryException as e:
                _logger.warning('MailDeliveryException while sending digest %d. Digest is now scheduled for next cron update.', digest.id)

    # ------------------------------------------------------------
    # KPIS
    # ------------------------------------------------------------

    def compute_kpis(self, company, user):
        """ Compute KPIs to display in the digest template. It is expected to be
        a list of KPIs, each containing values for 3 columns display.

        :return list: result [{
            'kpi_name': 'kpi_mail_message',
            'kpi_fullname': 'Messages',  # translated
            'kpi_action': 'crm.crm_lead_action_pipeline',  # xml id of an action to execute
            'kpi_col1': {
                'value': '12.0',
                'margin': 32.36,
                'col_subtitle': 'Yesterday',  # translated
            },
            'kpi_col2': { ... },
            'kpi_col3':  { ... },
        }, { ... }] """
        self.ensure_one()
        digest_fields = self._get_kpi_fields()
        invalid_fields = []
        kpis = [
            dict(kpi_name=field_name,
                 kpi_fullname=self._fields[field_name].string,
                 kpi_action=False,
                 kpi_col1=dict(),
                 kpi_col2=dict(),
                 kpi_col3=dict(),
                 )
            for field_name in digest_fields
        ]
        kpis_actions = self._compute_kpis_actions(company, user)

        for col_index, (tf_name, tf) in enumerate(self._compute_timeframes(company)):
            digest = self.with_context(start_date=tf[0][0], end_date=tf[0][1]).with_user(user).with_company(company)
            previous_digest = self.with_context(start_date=tf[1][0], end_date=tf[1][1]).with_user(user).with_company(company)
            for index, field_name in enumerate(digest_fields):
                kpi_values = kpis[index]
                kpi_values['kpi_action'] = kpis_actions.get(field_name)
                try:
                    compute_value = digest[field_name + '_value']
                    # Context start and end date is different each time so invalidate to recompute.
                    digest.invalidate_cache([field_name + '_value'])
                    previous_value = previous_digest[field_name + '_value']
                    # Context start and end date is different each time so invalidate to recompute.
                    previous_digest.invalidate_cache([field_name + '_value'])
                except AccessError:  # no access rights -> just skip that digest details from that user's digest email
                    invalid_fields.append(field_name)
                    continue
                margin = self._get_margin_value(compute_value, previous_value)
                if self._fields['%s_value' % field_name].type == 'monetary':
                    converted_amount = tools.format_decimalized_amount(compute_value)
                    compute_value = self._format_currency_amount(converted_amount, company.currency_id)
                kpi_values['kpi_col%s' % (col_index + 1)].update({
                    'value': compute_value,
                    'margin': margin,
                    'col_subtitle': tf_name,
                })

        # filter failed KPIs
        return [kpi for kpi in kpis if kpi['kpi_name'] not in invalid_fields]

    def compute_tips(self, company, user, tips_count=1, consumed=True):
        tips = self.env['digest.tip'].search([
            ('user_ids', '!=', user.id),
            '|', ('group_id', 'in', user.groups_id.ids), ('group_id', '=', False)
        ], limit=tips_count)
        tip_descriptions = [
            self.env['mail.render.mixin']._render_template(tools.html_sanitize(tip.tip_description), 'digest.tip', tip.ids, post_process=True)[tip.id]
            for tip in tips
        ]
        if consumed:
            tips.user_ids += user
        return tip_descriptions

    def _compute_kpis_actions(self, company, user):
        """ Give an optional action to display in digest email linked to some KPIs.

        :return dict: key: kpi name (field name), value: an action that will be
          concatenated with /web#action={action}
        """
        return {}

    def compute_preferences(self, company, user):
        """ Give an optional text for preferences, like a shortcut for configuration.

        :return string: html to put in template
        """
        preferences = []
        if self._context.get('digest_slowdown'):
            preferences.append(_("We have noticed you did not connect these last few days so we've automatically switched your preference to weekly Digests."))
        elif self.periodicity == 'daily' and user.has_group('base.group_erp_manager'):
            preferences.append('<p>%s<br /><a href="/digest/%s/set_periodicity?periodicity=weekly" target="_blank" style="color:#875A7B; font-weight: bold;">%s</a></p>' % (
                _('Prefer a broader overview ?'),
                self.id,
                _('Switch to weekly Digests')
            ))
        if user.has_group('base.group_erp_manager'):
            preferences.append('<p>%s<br /><a href="/web#view_type=form&amp;model=%s&amp;id=%s" target="_blank" style="color:#875A7B; font-weight: bold;">%s</a></p>' % (
                _('Want to customize this email?'),
                self._name,
                self.id,
                _('Choose the metrics you care about')
            ))

        return preferences

    def _get_next_run_date(self):
        self.ensure_one()
        if self.periodicity == 'daily':
            delta = relativedelta(days=1)
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
        return [
            (_('Yesterday'), (
                (start_date + relativedelta(days=-1), start_date),
                (start_date + relativedelta(days=-2), start_date + relativedelta(days=-1)))
            ), (_('Last 7 Days'), (
                (start_date + relativedelta(weeks=-1), start_date),
                (start_date + relativedelta(weeks=-2), start_date + relativedelta(weeks=-1)))
            ), (_('Last 30 Days'), (
                (start_date + relativedelta(months=-1), start_date),
                (start_date + relativedelta(months=-2), start_date + relativedelta(months=-1)))
            )
        ]

    # ------------------------------------------------------------
    # FORMATTING / TOOLS
    # ------------------------------------------------------------

    def _get_kpi_fields(self):
        return [field_name for field_name, field in self._fields.items()
                if field.type == 'boolean' and field_name.startswith(('kpi_', 'x_kpi_', 'x_studio_kpi_')) and self[field_name]
               ]

    def _get_margin_value(self, value, previous_value=0.0):
        margin = 0.0
        if (value != previous_value) and (value != 0.0 and previous_value != 0.0):
            margin = float_round((float(value-previous_value) / previous_value or 1) * 100, precision_digits=2)
        return margin

    def _check_daily_logs(self):
        three_days_ago = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - relativedelta(days=3)
        to_slowdown = self.env['digest.digest']
        for digest in self.filtered(lambda digest: digest.periodicity == 'daily'):
            users_logs = self.env['res.users.log'].sudo().search_count([
                ('create_uid', 'in', digest.user_ids.ids),
                ('create_date', '>=', three_days_ago)
            ])
            if not users_logs:
                to_slowdown += digest
        return to_slowdown

    def _format_currency_amount(self, amount, currency_id):
        pre = currency_id.position == 'before'
        symbol = u'{symbol}'.format(symbol=currency_id.symbol or '')
        return u'{pre}{0}{post}'.format(amount, pre=symbol if pre else '', post=symbol if not pre else '')
