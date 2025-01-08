# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from markupsafe import Markup
from werkzeug.urls import url_encode, url_join

from odoo import api, Command, fields, models, tools, _
from odoo.addons.base.models.ir_mail_server import MailDeliveryException
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class DigestDigestKpi(models.Model):
    _name = 'digest.digest.kpi'
    _description = 'Digest KPI'
    _order = 'sequence, id'

    sequence = fields.Integer('Sequence')
    opt_out_user_ids = fields.Many2many('res.users', string='Opted Out Users', domain="[('id', 'in', digest.user_ids)]",
                                        groups="base.group_system")
    is_opted_in = fields.Boolean('Is Opted In', compute_sudo=True, compute="_compute_is_opted_in", inverse="_inverse_is_opted_in")
    digest = fields.Many2one('digest.digest', 'Digest', required=True, ondelete='cascade')
    kpi_id = fields.Many2one('digest.kpi', 'KPI', required=True, ondelete='cascade')

    name = fields.Char(related='kpi_id.name')

    module_name = fields.Char(related='kpi_id.module_id.name', compute_sudo=True)
    icon_url = fields.Char(related='kpi_id.icon_url')

    _digest_kpi_uniq = models.Constraint('UNIQUE (digest, kpi_id)', 'Kpi must be unique per digest.')

    @api.depends('opt_out_user_ids')
    @api.depends_context('uid')
    def _compute_is_opted_in(self):
        opted_out_records = self.filtered(lambda d: self.env.user in d.opt_out_user_ids)
        opted_out_records.is_opted_in = False
        (self - opted_out_records).is_opted_in = True

    def _inverse_is_opted_in(self):
        to_remove = self.env['digest.digest.kpi']
        to_add = self.env['digest.digest.kpi']
        for digest_kpi in self:
            is_opted_in = self.env.user not in self.opt_out_user_ids
            if is_opted_in == digest_kpi.is_opted_in:
                continue
            if digest_kpi.is_opted_in:
                to_remove |= digest_kpi
            else:
                to_add |= digest_kpi
        to_add.sudo().write({'opt_out_user_ids': [Command.link(self.env.user.id)]})
        to_remove.sudo().write({'opt_out_user_ids': [Command.unlink(self.env.user.id)]})

    def action_edit_kpi(self):
        return self.kpi_id.action_edit()

    def action_remove_kpi_from_digest(self):
        self.ensure_one()
        self.digest.write({'kpi_ids': [Command.unlink(self.kpi_id.id)]})

    def action_toggle_opt_in_out(self):
        self.ensure_one()
        self.sudo().is_opted_in = not self.is_opted_in


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
    is_subscribed = fields.Boolean('Is user subscribed', compute='_compute_is_subscribed')
    state = fields.Selection([('activated', 'Activated'), ('deactivated', 'Deactivated')], string='Status', readonly=True, default='activated')
    digest_kpi_ids = fields.One2many('digest.digest.kpi', 'digest')
    kpi_ids = fields.Many2many(string='KPIs', comodel_name='digest.kpi',
                               relation='digest_digest_kpi', column1='digest', column2='kpi_id',
                               readonly=False)

    @api.depends('user_ids')
    def _compute_is_subscribed(self):
        for digest in self:
            digest.is_subscribed = self.env.user in digest.user_ids

    @api.onchange('periodicity')
    def _onchange_periodicity(self):
        self.next_run_date = self._get_next_run_date()

    @api.model_create_multi
    def create(self, vals_list):
        digests = super().create(vals_list)
        for digest in digests:
            if not digest.next_run_date:
                digest.next_run_date = digest._get_next_run_date()
        # Ensure digest_kpi_ids.sequence are initialized with related kpi sequence when added through kpi_ids.
        if any('digest_kpi_ids' not in vals for vals in vals_list):
            digests.invalidate_recordset(['digest_kpi_ids'])  # as kpi_ids and kpi_digest_ids are the same relation
            for digest, vals in zip(digests, vals_list):
                if 'digest_kpi_ids' in vals:
                    continue
                for digest_kpi in digest.digest_kpi_ids:
                    digest_kpi.sequence = digest_kpi.kpi_id.sequence
        return digests

    def write(self, vals):
        """ Ensure digest_kpi_ids.sequence are initialized with related kpi sequence when added through kpi_ids. """
        kpi_before = {digest.id: digest.kpi_ids for digest in self}
        res = super().write(vals)
        if 'digest_kpi_ids' in vals:
            return res
        self.invalidate_recordset(['digest_kpi_ids'])  # as kpi_ids and kpi_digest_ids are the same relation
        for digest in self:
            added_kpi = digest.kpi_ids - kpi_before[digest.id]
            for digest_kpi in digest.digest_kpi_ids:
                if digest_kpi.kpi_id in added_kpi:
                    digest_kpi.sequence = digest_kpi.kpi_id.sequence
        return res

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

    def _action_send(self, update_periodicity=True, ignore_error=False):
        """ Send digests email to all the registered users.

        :param bool update_periodicity: if True, check user logs to update
          periodicity of digests. Purpose is to slow down digest whose users
          do not connect to avoid spam;
        """
        to_slowdown = self._check_daily_logs() if update_periodicity else self.env['digest.digest']

        all_recipients_user_companies = (self.user_ids or self.env.user).company_id
        values_by_kpi_id_by_company_id = self.kpi_ids._calculate_values_by_company(all_recipients_user_companies)
        # TODO: prefetch user.groups, opt_out_user_ids
        for digest in self:
            for user in digest.user_ids:
                try:
                    values_by_kpi = values_by_kpi_id_by_company_id[user.company_id.id]
                    digest.with_context(
                        digest_slowdown=digest in to_slowdown,
                        lang=user.lang,
                    )._action_send_to_user(user, tips_count=1, values_by_kpi=values_by_kpi)
                except MailDeliveryException:
                    if not ignore_error:
                        raise
                    _logger.warning(
                        'MailDeliveryException while sending digest %d to user %d. '
                        'Digest is now scheduled for next cron update.',
                        digest.id, user.id)
                except UserError:
                    if not ignore_error:
                        raise
            if digest in to_slowdown:
                digest.periodicity = digest._get_next_periodicity()[0]
            digest.next_run_date = digest._get_next_run_date()

    def _action_send_to_user(self, user, tips_count=1, consume_tips=True, values_by_kpi=None):
        self.ensure_one()
        digest_kpi_authorized = self.digest_kpi_ids.filtered(
            lambda dk: not dk.kpi_id.group_ids or user.all_group_ids & dk.kpi_id.group_ids)
        if not digest_kpi_authorized:
            raise UserError(_('The digest "%(digest_name)s" for "%(user_name)s" is empty '
                              '(probably because the users have no access to the KPIs).',
                              user_name=user.name, digest_name=self.name))
        kpis = digest_kpi_authorized.filtered(lambda dk: user not in dk.opt_out_user_ids).kpi_id
        if not values_by_kpi:
            values_by_kpi = kpis._calculate_values_by_company(self.company_id)[self.company_id.id]
        kpis = kpis.filtered(lambda kpi: not values_by_kpi[kpi.id].get('error', False))
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
                'kpi_data': kpis._get_kpi_data(values_by_kpi),
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

    def action_add_kpi(self):
        self.ensure_one()
        form = self.env.ref('digest.digest_digest_view_form_add_remove_kpi', False)
        return {
            'name': _('Add/Remove KPIs in "%(digest_name)s"', digest_name=self.name),
            'type': 'ir.actions.act_window',
            'views': [(form.id, 'form')],
            'view_id': form.id,
            'target': 'new',
            'res_model': 'digest.digest',
            'res_id': self.id,
        }

    def action_create_kpi(self):
        self.ensure_one()
        return {
            'name': _('Create Custom KPI'),
            'type': 'ir.actions.act_window',
            'res_model': 'digest.kpi',
            'view_mode': 'form',
            'target': 'new',
        }

    @api.model
    def _cron_send_digest_email(self):
        digests = self.search([('next_run_date', '<=', fields.Date.today()), ('state', '=', 'activated')])
        digests._action_send(ignore_error=True)

    def _get_unsubscribe_token(self, user_id):
        """Generate a secure hash for this digest and user. It allows to
        unsubscribe from a digest while keeping some security in that process.

        :param int user_id: ID of the user to unsubscribe
        """
        return tools.hmac(self.env(su=True), 'digest-unsubscribe', (self.id, user_id))

    # ------------------------------------------------------------
    # KPIS
    # ------------------------------------------------------------

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
        if user.has_group('base.group_user'):
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

    # ------------------------------------------------------------
    # FORMATTING / TOOLS
    # ------------------------------------------------------------

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
