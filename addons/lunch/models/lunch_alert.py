# Part of Odoo. See LICENSE file for full copyright and licensing details.
import pytz
import logging

from odoo import api, fields, models, _
from odoo.osv import expression

from .lunch_supplier import float_to_time
from datetime import datetime, timedelta
from textwrap import dedent

from odoo.addons.base.models.res_partner import _tz_get

_logger = logging.getLogger(__name__)
WEEKDAY_TO_NAME = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
CRON_DEPENDS = {'name', 'active', 'mode', 'until', 'notification_time', 'notification_moment', 'tz'}


class LunchAlert(models.Model):
    """ Alerts to display during a lunch order. An alert can be specific to a
    given day, weekly or daily. The alert is displayed from start to end hour. """
    _name = 'lunch.alert'
    _description = 'Lunch Alert'
    _order = 'write_date desc, id'

    name = fields.Char('Alert Name', required=True, translate=True)
    message = fields.Html('Message', required=True, translate=True)

    mode = fields.Selection([
        ('alert', 'Alert in app'),
        ('chat', 'Chat notification')], string='Display', default='alert')
    recipients = fields.Selection([
        ('everyone', 'Everyone'),
        ('last_week', 'Employee who ordered last week'),
        ('last_month', 'Employee who ordered last month'),
        ('last_year', 'Employee who ordered last year')], string='Recipients', default='everyone')
    notification_time = fields.Float(default=10.0, string='Notification Time')
    notification_moment = fields.Selection([
        ('am', 'AM'),
        ('pm', 'PM')], default='am', required=True)
    tz = fields.Selection(_tz_get, string='Timezone', required=True, default=lambda self: self.env.user.tz or 'UTC')
    cron_id = fields.Many2one('ir.cron', ondelete='cascade', required=True, readonly=True)

    until = fields.Date('Show Until')
    mon = fields.Boolean(default=True)
    tue = fields.Boolean(default=True)
    wed = fields.Boolean(default=True)
    thu = fields.Boolean(default=True)
    fri = fields.Boolean(default=True)
    sat = fields.Boolean(default=True)
    sun = fields.Boolean(default=True)

    available_today = fields.Boolean('Is Displayed Today',
                                     compute='_compute_available_today', search='_search_available_today')

    active = fields.Boolean('Active', default=True)

    location_ids = fields.Many2many('lunch.location', string='Location')

    _notification_time_range = models.Constraint(
        'CHECK(notification_time >= 0 and notification_time <= 12)',
        'Notification time must be between 0 and 12',
    )

    @api.depends('mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun')
    def _compute_available_today(self):
        today = fields.Date.context_today(self)
        fieldname = WEEKDAY_TO_NAME[today.weekday()]

        for alert in self:
            alert.available_today = alert.until > today if alert.until else True and alert[fieldname]

    def _search_available_today(self, operator, value):
        if (not operator in ['=', '!=']) or (not value in [True, False]):
            return []

        searching_for_true = (operator == '=' and value) or (operator == '!=' and not value)
        today = fields.Date.context_today(self)
        fieldname = WEEKDAY_TO_NAME[today.weekday()]

        return expression.AND([
            [(fieldname, operator, value)],
            expression.OR([
                [('until', '=', False)],
                [('until', '>' if searching_for_true else '<', today)],
            ])
        ])

    def _sync_cron(self):
        """ Synchronise the related cron fields to reflect this alert """
        for alert in self:
            alert = alert.with_context(tz=alert.tz)

            cron_required = (
                alert.active
                and alert.mode == 'chat'
                and (not alert.until or fields.Date.context_today(alert) <= alert.until)
            )

            sendat_tz = pytz.timezone(alert.tz).localize(datetime.combine(
                fields.Date.context_today(alert, fields.Datetime.now()),
                float_to_time(alert.notification_time, alert.notification_moment)))
            cron = alert.cron_id.sudo()
            lc = cron.lastcall
            if ((
                lc and sendat_tz.date() <= fields.Datetime.context_timestamp(alert, lc).date()
            ) or (
                not lc and sendat_tz <= fields.Datetime.context_timestamp(alert, fields.Datetime.now())
            )):
                sendat_tz += timedelta(days=1)
            sendat_utc = sendat_tz.astimezone(pytz.UTC).replace(tzinfo=None)

            cron.name = f"Lunch: alert chat notification ({alert.name})"
            cron.active = cron_required
            cron.nextcall = sendat_utc
            cron.code = dedent(f"""\
                # This cron is dynamically controlled by {self._description}.
                # Do NOT modify this cron, modify the related record instead.
                env['{self._name}'].browse([{alert.id}])._notify_chat()""")

    @api.model_create_multi
    def create(self, vals_list):
        crons = self.env['ir.cron'].sudo().create([
            {
                'user_id': self.env.ref('base.user_root').id,
                'active': False,
                'interval_type': 'days',
                'interval_number': 1,
                'name': "Lunch: alert chat notification",
                'model_id': self.env['ir.model']._get_id(self._name),
                'state': 'code',
                'code': "",
            }
            for _ in range(len(vals_list))
        ])
        self.env['ir.model.data'].sudo().create([{
            'name': f'lunch_alert_cron_sa_{cron.ir_actions_server_id.id}',
            'module': 'lunch',
            'res_id': cron.ir_actions_server_id.id,
            'model': 'ir.actions.server',
            # noupdate is set to true to avoid to delete record at module update
            'noupdate': True,
        } for cron in crons])
        for vals, cron in zip(vals_list, crons):
            vals['cron_id'] = cron.id

        alerts = super().create(vals_list)
        alerts._sync_cron()
        return alerts

    def write(self, values):
        res = super().write(values)
        if not CRON_DEPENDS.isdisjoint(values):
            self._sync_cron()
        return res

    def unlink(self):
        crons = self.cron_id.sudo()
        server_actions = crons.ir_actions_server_id
        res = super().unlink()
        crons.unlink()
        server_actions.unlink()
        return res

    def _notify_chat(self):
        # Called daily by cron
        self.ensure_one()

        if not self.available_today:
            _logger.warning("cancelled, not available today")
            if self.cron_id and self.until and fields.Date.context_today(self) > self.until:
                self.cron_id.unlink()
                self.cron_id = False
            return

        if not self.active or self.mode != 'chat':
            raise ValueError("Cannot send a chat notification in the current state")

        order_domain = [('state', '!=', 'cancelled')]

        if self.location_ids.ids:
            order_domain = expression.AND([order_domain, [('user_id.last_lunch_location_id', 'in', self.location_ids.ids)]])

        if self.recipients != 'everyone':
            weeksago = fields.Date.today() - timedelta(weeks=(
                1 if self.recipients == 'last_week' else
                4 if self.recipients == 'last_month' else
                52  # if self.recipients == 'last_year'
            ))
            order_domain = expression.AND([order_domain, [('date', '>=', weeksago)]])

        partners = self.env['lunch.order'].search(order_domain).user_id.partner_id
        if partners:
            self.env['mail.thread'].message_notify(
                model=self._name,
                res_id=self.id,
                body=self.message,
                partner_ids=partners.ids,
                subject=_('Your Lunch Order'),
            )
