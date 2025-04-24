# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pytz

from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from markupsafe import Markup
from werkzeug.urls import url_encode

from odoo import api, fields, models, tools, _
from odoo.addons.base.models.ir_mail_server import MailDeliveryException
from odoo.exceptions import AccessError
from odoo.fields import Domain
from odoo.tools.float_utils import float_round
from odoo.tools.urls import urljoin as url_join

_logger = logging.getLogger(__name__)


class DigestDigest(models.Model):
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
    next_run_date = fields.Date(string='Next Mailing Date')
    currency_id = fields.Many2one(related="company_id.currency_id", string='Currency', readonly=False)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company.id)
    available_fields = fields.Char(compute='_compute_available_fields')
    is_subscribed = fields.Boolean('Is user subscribed', compute='_compute_is_subscribed')
    state = fields.Selection([('activated', 'Activated'), ('deactivated', 'Deactivated')], string='Status', readonly=True, default='activated')
    # First base-related KPIs
    kpi_res_users_connected = fields.Boolean('Connected Users')
    kpi_res_users_connected_value = fields.Integer(compute='_compute_kpi_res_users_connected_value')
    kpi_mail_message_total = fields.Boolean('Messages Sent')
    kpi_mail_message_total_value = fields.Integer(compute='_compute_kpi_mail_message_total_value')

    @api.depends('user_ids')
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
        """Get the parameters used to computed the KPI value."""
        companies = self.company_id
        if any(not digest.company_id for digest in self):
            # No company: we will use the current company to compute the KPIs
            companies |= self.env.company

        return (
            fields.Datetime.to_string(self.env.context.get('start_datetime')),
            fields.Datetime.to_string(self.env.context.get('end_datetime')),
            companies,
        )

    def _compute_kpi_res_users_connected_value(self):
        self._calculate_company_based_kpi(
            'res.users',
            'kpi_res_users_connected_value',
            date_field='login_date',
        )

    def _compute_kpi_mail_message_total_value(self):
        start, end, __ = self._get_kpi_compute_parameters()
        self.kpi_mail_message_total_value = self.env['mail.message'].search_count([
            ('create_date', '>=', start),
            ('create_date', '<', end),
            ('subtype_id', '=', self.env.ref('mail.mt_comment').id),
            ('message_type', 'in', ('comment', 'email', 'email_outgoing')),
        ])

    @api.onchange('periodicity')
    def _onchange_periodicity(self):
        self.next_run_date = self._get_next_run_date()

    @api.model_create_multi
    def create(self, vals_list):
        digests = super().create(vals_list)
        for digest in digests:
            if not digest.next_run_date:
                digest.next_run_date = digest._get_next_run_date()
        return digests

    # ------------------------------------------------------------
    # ACTIONS
    # ------------------------------------------------------------

    def action_subscribe(self):
        if self.env.user._is_internal() and self.env.user not in self.user_ids:
            self._action_subscribe_users(self.env.user)

    def _action_subscribe_users(self, users):
        """ Private method to manage subscriptions. Done as sudo() to speedup
        computation and avoid ACLs issues. """
        self.sudo().user_ids |= users

    def action_unsubscribe(self):
        if self.env.user._is_internal() and self.env.user in self.user_ids:
            self._action_unsubscribe_users(self.env.user)

    def _action_unsubscribe_users(self, users):
        """ Private method to manage subscriptions. Done as sudo() to speedup
        computation and avoid ACLs issues. """
        self.sudo().user_ids -= users

    def action_activate(self):
        self.state = 'activated'

    def action_deactivate(self):
        self.state = 'deactivated'

    def action_set_periodicity(self, periodicity):
        self.periodicity = periodicity

    def action_send(self):
        """ Send digests emails to all the registered users. """
        return self._action_send(update_periodicity=True)

    def action_send_manual(self):
        """ Manually send digests emails to all registered users. In that case
        do not update periodicity as this is not an automation rule that could
        be considered as unwanted spam. """
        return self._action_send(update_periodicity=False)

    def _action_send(self, update_periodicity=True):
        """ Send digests email to all the registered users.

        :param bool update_periodicity: if True, check user logs to update
          periodicity of digests. Purpose is to slow down digest whose users
          do not connect to avoid spam;
        """
        to_slowdown = self._check_daily_logs() if update_periodicity else self.env['digest.digest']

        for digest in self:
            for user in digest.user_ids:
                digest.with_context(
                    digest_slowdown=digest in to_slowdown,
                    lang=user.lang
                )._action_send_to_user(user, tips_count=1)
            if digest in to_slowdown:
                digest.periodicity = digest._get_next_periodicity()[0]
            digest.next_run_date = digest._get_next_run_date()

    def _action_send_to_user(self, user, tips_count=1, consume_tips=True):
        unsubscribe_token = self._get_unsubscribe_token(user.id)

        rendered_body = self.env['mail.render.mixin']._render_template(
            'digest.digest_mail_main',
            'digest.digest',
            self.ids,
            engine='qweb_view',
            add_context={
                'title': self.name,
                'top_button_label': _('Connect'),
                'top_button_url': self.get_base_url(),
                'company': user.company_id,
                'user': user,
                'unsubscribe_token': unsubscribe_token,
                'tips_count': tips_count,
                'formatted_date': datetime.today().strftime('%B %d, %Y'),
                'display_mobile_banner': True,
                'kpi_data': self._compute_kpis(user.company_id, user),
                'tips': self._compute_tips(user.company_id, user, tips_count=tips_count, consumed=consume_tips),
                'preferences': self._compute_preferences(user.company_id, user),
            },
            options={
                'preserve_comments': True,
                'post_process': True,
            },
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
        unsub_params = url_encode({
            "token": unsubscribe_token,
            "user_id": user.id,
        })
        unsub_url = url_join(
            self.get_base_url(),
            f'/digest/{self.id}/unsubscribe_oneclik?{unsub_params}'
        )
        mail_values = {
            'auto_delete': True,
            'author_id': self.env.user.partner_id.id,
            'body_html': full_mail,
            'email_from': (
                self.company_id.partner_id.email_formatted
                or self.env.user.email_formatted
                or self.env.ref('base.user_root').email_formatted
            ),
            'email_to': user.email_formatted,
            # Add headers that allow the MUA to offer a one click button to unsubscribe (requires DKIM to work)
            'headers': {
                'List-Unsubscribe': f'<{unsub_url}>',
                'List-Unsubscribe-Post': 'List-Unsubscribe=One-Click',
                'X-Auto-Response-Suppress': 'OOF',  # avoid out-of-office replies from MS Exchange
            },
            'state': 'outgoing',
            'subject': '%s: %s' % (user.company_id.name, self.name),
        }
        self.env['mail.mail'].sudo().create(mail_values)
        return True

    @api.model
    def _cron_send_digest_email(self):
        digests = self.search([('next_run_date', '<=', fields.Date.today()), ('state', '=', 'activated')])
        for digest in digests:
            try:
                digest.action_send()
            except MailDeliveryException as e:
                _logger.warning('MailDeliveryException while sending digest %d. Digest is now scheduled for next cron update.', digest.id)

    def _get_unsubscribe_token(self, user_id):
        """Generate a secure hash for this digest and user. It allows to
        unsubscribe from a digest while keeping some security in that process.

        :param int user_id: ID of the user to unsubscribe
        """
        return tools.hmac(self.env(su=True), 'digest-unsubscribe', (self.id, user_id))

    # ------------------------------------------------------------
    # KPIS
    # ------------------------------------------------------------

    def _compute_kpis(self, company, user):
        """ Compute KPIs to display in the digest template. It is expected to be
        a list of KPIs, each containing values for 3 columns display.

        :return: result [{
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
                 kpi_fullname=self.env['ir.model.fields']._get(self._name, field_name).field_description,
                 kpi_action=False,
                 kpi_col1=dict(),
                 kpi_col2=dict(),
                 kpi_col3=dict(),
                 )
            for field_name in digest_fields
        ]
        kpis_actions = self._compute_kpis_actions(company, user)

        for col_index, (tf_name, tf) in enumerate(self._compute_timeframes(company)):
            digest = self.with_context(start_datetime=tf[0][0], end_datetime=tf[0][1]).with_user(user).with_company(company)
            previous_digest = self.with_context(start_datetime=tf[1][0], end_datetime=tf[1][1]).with_user(user).with_company(company)
            for index, field_name in enumerate(digest_fields):
                kpi_values = kpis[index]
                kpi_values['kpi_action'] = kpis_actions.get(field_name)
                try:
                    compute_value = digest[field_name + '_value']
                    # Context start and end date is different each time so invalidate to recompute.
                    digest.invalidate_model([field_name + '_value'])
                    previous_value = previous_digest[field_name + '_value']
                    # Context start and end date is different each time so invalidate to recompute.
                    previous_digest.invalidate_model([field_name + '_value'])
                except AccessError:  # no access rights -> just skip that digest details from that user's digest email
                    invalid_fields.append(field_name)
                    continue
                margin = self._get_margin_value(compute_value, previous_value)
                if self._fields['%s_value' % field_name].type == 'monetary':
                    converted_amount = tools.misc.format_decimalized_amount(compute_value)
                    compute_value = self._format_currency_amount(converted_amount, company.currency_id)
                elif self._fields['%s_value' % field_name].type == 'float':
                    compute_value = "%.2f" % compute_value

                kpi_values['kpi_col%s' % (col_index + 1)].update({
                    'value': compute_value,
                    'margin': margin,
                    'col_subtitle': tf_name,
                })

        # filter failed KPIs
        return [kpi for kpi in kpis if kpi['kpi_name'] not in invalid_fields]

    def _compute_tips(self, company, user, tips_count=1, consumed=True):
        tips = self.env['digest.tip'].search([
            ('user_ids', '!=', user.id),
            '|', ('group_id', 'in', user.all_group_ids.ids), ('group_id', '=', False)
        ], limit=tips_count)
        tip_descriptions = [
            tools.html_sanitize(
                self.env['mail.render.mixin'].sudo()._render_template(
                    tip.tip_description,
                    'digest.tip',
                    tip.ids,
                    engine="qweb",
                    options={'post_process': True},
                )[tip.id]
            )
            for tip in tips
        ]
        if consumed:
            tips.user_ids += user
        return tip_descriptions

    def _compute_kpis_actions(self, company, user):
        """ Give an optional action to display in digest email linked to some KPIs.

        :returns: key: kpi name (field name), value: an action that will be
          concatenated with /odoo/action-{action}
        :rtype: dict
        """
        return {}

    def _compute_preferences(self, company, user):
        """ Give an optional text for preferences, like a shortcut for configuration.

        :returns: html to put in template
        :rtype: str
        """
        preferences = []
        if self.env.context.get('digest_slowdown'):
            _dummy, new_perioridicy_str = self._get_next_periodicity()
            preferences.append(
                _("We have noticed you did not connect these last few days. We have automatically switched your preference to %(new_perioridicy_str)s Digests.",
                  new_perioridicy_str=new_perioridicy_str)
            )
        elif self.periodicity == 'daily' and user.has_group('base.group_erp_manager'):
            preferences.append(Markup('<p>%s<br /><a href="%s" target="_blank" style="color:#017e84; font-weight: bold;">%s</a></p>') % (
                _('Prefer a broader overview?'),
                f'/digest/{self.id:d}/set_periodicity?periodicity=weekly',
                _('Switch to weekly Digests')
            ))
        if user.has_group('base.group_erp_manager'):
            preferences.append(Markup('<p>%s<br /><a href="%s" target="_blank" style="color:#017e84; font-weight: bold;">%s</a></p>') % (
                _('Want to customize this email?'),
                f'/odoo/{self._name}/{self.id:d}',
                _('Choose the metrics you care about')
            ))

        return preferences

    def _get_next_run_date(self):
        self.ensure_one()
        if self.periodicity == 'daily':
            delta = relativedelta(days=1)
        elif self.periodicity == 'weekly':
            delta = relativedelta(weeks=1)
        elif self.periodicity == 'monthly':
            delta = relativedelta(months=1)
        else:
            delta = relativedelta(months=3)
        return date.today() + delta

    def _compute_timeframes(self, company):
        start_datetime = datetime.utcnow()
        tz_name = company.resource_calendar_id.tz
        if tz_name:
            start_datetime = pytz.timezone(tz_name).localize(start_datetime)
        return [
            (_('Last 24 hours'), (
                (start_datetime + relativedelta(days=-1), start_datetime),
                (start_datetime + relativedelta(days=-2), start_datetime + relativedelta(days=-1)))
            ), (_('Last 7 Days'), (
                (start_datetime + relativedelta(weeks=-1), start_datetime),
                (start_datetime + relativedelta(weeks=-2), start_datetime + relativedelta(weeks=-1)))
            ), (_('Last 30 Days'), (
                (start_datetime + relativedelta(months=-1), start_datetime),
                (start_datetime + relativedelta(months=-2), start_datetime + relativedelta(months=-1)))
            )
        ]

    # ------------------------------------------------------------
    # FORMATTING / TOOLS
    # ------------------------------------------------------------

    def _calculate_company_based_kpi(self, model, digest_kpi_field, date_field='create_date',
                                     additional_domain=None, sum_field=None):
        """Generic method that computes the KPI on a given model.

        :param model: Model on which we will compute the KPI
            This model must have a "company_id" field
        :param digest_kpi_field: Field name on which we will write the KPI
        :param date_field: Field used for the date range
        :param additional_domain: Additional domain
        :param sum_field: Field to sum to obtain the KPI,
            if None it will count the number of records
        """
        start, end, companies = self._get_kpi_compute_parameters()

        base_domain = Domain([
            ('company_id', 'in', companies.ids),
            (date_field, '>=', start),
            (date_field, '<', end),
        ])

        if additional_domain:
            base_domain &= Domain(additional_domain)

        values = self.env[model]._read_group(
            domain=base_domain,
            groupby=['company_id'],
            aggregates=[f'{sum_field}:sum'] if sum_field else ['__count'],
        )

        values_per_company = {company.id: agg for company, agg in values}
        for digest in self:
            company = digest.company_id or self.env.company
            digest[digest_kpi_field] = values_per_company.get(company.id, 0)

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
        """ Badly named method that checks user logs and slowdown the sending
        of digest emails based on recipients being away. """
        today = datetime.now().replace(microsecond=0)
        to_slowdown = self.env['digest.digest']
        for digest in self:
            if digest.periodicity == 'daily':  # 2 days ago
                limit_dt = today - relativedelta(days=2)
            elif digest.periodicity == 'weekly':  # 1 week ago
                limit_dt = today - relativedelta(days=7)
            elif digest.periodicity == 'monthly':  # 1 month ago
                limit_dt = today - relativedelta(months=1)
            elif digest.periodicity == 'quarterly':  # 3 month ago
                limit_dt = today - relativedelta(months=3)
            users_logs = self.env['res.users.log'].sudo().search_count([
                ('create_uid', 'in', digest.user_ids.ids),
                ('create_date', '>=', limit_dt)
            ])
            if not users_logs:
                to_slowdown += digest
        return to_slowdown

    def _get_next_periodicity(self):
        if self.periodicity == 'daily':
            return 'weekly', _('weekly')
        if self.periodicity == 'weekly':
            return 'monthly', _('monthly')
        return 'quarterly', _('quarterly')

    def _format_currency_amount(self, amount, currency_id):
        pre = currency_id.position == 'before'
        symbol = u'{symbol}'.format(symbol=currency_id.symbol or '')
        return u'{pre}{0}{post}'.format(amount, pre=symbol if pre else '', post=symbol if not pre else '')
