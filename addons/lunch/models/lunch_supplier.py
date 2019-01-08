# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import math
import pytz

from datetime import datetime, time

from odoo import api, fields, models
from odoo.osv import expression
from odoo.tools import float_round

from odoo.addons.base.models.res_partner import _tz_get


WEEKDAY_TO_NAME = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']

def float_to_time(hours, tz=None):
    """ Convert a number of hours into a time object. """
    if hours == 24.0:
        return time.max
    fractional, integral = math.modf(hours)
    res = time(int(integral), int(float_round(60 * fractional, precision_digits=0)), 0)
    if tz:
        res = res.replace(tzinfo=pytz.timezone(tz))
    return res

def time_to_float(t):
    return float_round(t.hour + t.minute/60 + t.second/3600, precision_digits=2)

class LunchSupplier(models.Model):
    _name = 'lunch.supplier'
    _description = 'Lunch Supplier'

    partner_id = fields.Many2one('res.partner', string='Linked partner', required=True)

    name = fields.Char('Name', related='partner_id.name')
    description = fields.Text('Description')

    email = fields.Char(related='partner_id.email')
    email_formatted = fields.Char(related='partner_id.email_formatted', readonly=True)
    phone = fields.Char(related='partner_id.phone')
    street = fields.Char(related='partner_id.street')
    street2 = fields.Char(related='partner_id.street2')
    zip_code = fields.Char(related='partner_id.zip')
    city = fields.Char(related='partner_id.city')
    state_id = fields.Many2one("res.country.state", related='partner_id.state_id')
    country_id = fields.Many2one('res.country', related='partner_id.country_id')

    vat = fields.Char(related='partner_id.vat')

    image = fields.Binary(related='partner_id.image', readonly=False)
    image_medium = fields.Binary(related='partner_id.image_medium', readonly=False)
    image_small = fields.Binary(related='partner_id.image_small', readonly=False)

    send_by = fields.Selection([
        ('phone', 'Phone'),
        ('mail', 'Email'),
    ], 'Send Order By', default='phone')
    automatic_email_send = fields.Boolean('Automatic Email Sending')
    automatic_email_time = fields.Float('Hour')

    recurrency = fields.Selection([('once', 'Specific Day'), ('reccurent', 'Reccurent')], 'Recurrency', default='once')
    recurrency_from = fields.Float('From')
    recurrency_to = fields.Float('To')
    recurrency_date = fields.Date('Day', default=fields.Date.today())
    recurrency_date_from = fields.Datetime('from', compute='_compute_recurrency_date_from', store=True)
    recurrency_date_to = fields.Datetime('to', compute='_compute_recurrency_date_to', store=True)
    recurrency_monday = fields.Boolean('Monday')
    recurrency_tuesday = fields.Boolean('Tuesday')
    recurrency_wednesday = fields.Boolean('Wednesday')
    recurrency_thursday = fields.Boolean('Thursday')
    recurrency_friday = fields.Boolean('Friday')
    recurrency_saturday = fields.Boolean('Saturday')
    recurrency_sunday = fields.Boolean('Sunday')

    available_today = fields.Boolean('This is True when if the supplier is available today',
                                     compute='_compute_available_today', search='_search_available_today')

    tz = fields.Selection(_tz_get, string='Timezone', required=True, default='UTC')

    _sql_constraints = [
        ('automatic_email_time_range', 'CHECK(automatic_email_time >= 0 AND automatic_email_time <= 24)', 'Automatic Email Sending Time should be between 0 and 24'),
        ('recurrency_from', 'CHECK(recurrency_from >= 0 AND recurrency_from <= 24)', 'Recurrency From should be between 0 and 24'),
        ('recurrency_to', 'CHECK(recurrency_to >= 0 AND recurrency_to <= 24)', 'Recurrency To should be between 0 and 24')
    ]

    @api.model
    def _auto_email_send(self):
        """
            This method is called every 10 minutes via a cron.
            Its job is simply to get all the orders made for each supplier and send an email
            automatically to the supplier if the supplier is configured for it and we are ready
            to send it (usually at 11am or so)
        """
        records = self.search([('automatic_email_send', '=', True)])

        for supplier in records:
            send_at = datetime.combine(fields.Date.today(), float_to_time(supplier.automatic_email_time, supplier.tz)).astimezone(pytz.UTC).replace(tzinfo=None)
            if supplier.available_today and fields.Datetime.now() > send_at:
                orders = self.env['lunch.order'].search([('mail_sent', '=', False), ('supplier_ids', 'in', [supplier.id]), ('state', '=', 'ordered')])

                if orders:
                    order = {
                        'company_name': orders[0].company_id.name,
                        'currency_id': orders[0].currency_id.id,
                        'supplier_id': supplier.partner_id.id,
                        'supplier_name': supplier.name,
                        'supplier_email': supplier.email_formatted
                    }

                    lines = orders.mapped('order_line_ids').filtered(lambda line: line.supplier_id == supplier)
                    lines = [{'product': line.product_id.name, 'note': line.note, 'quantity': line.quantity, 'price': line.price} for line in lines]

                    order['amount_total'] = sum(line['price'] for line in lines)

                    self.env.ref('lunch.lunch_order_mail_supplier').with_context(order=order, lines=lines).send_mail(supplier.id)

                    orders.action_confirm(supplier)

    @api.depends('recurrency_date', 'recurrency_from')
    def _compute_recurrency_date_from(self):
        for supplier in self:
            if supplier.recurrency_date and supplier.recurrency_from:
                supplier.recurrency_date_from = datetime.combine(supplier.recurrency_date, float_to_time(supplier.recurrency_from))

    @api.depends('recurrency_date', 'recurrency_to')
    def _compute_recurrency_date_to(self):
        for supplier in self:
            if supplier.recurrency_date and supplier.recurrency_to:
                supplier.recurrency_date_to = datetime.combine(supplier.recurrency_date, float_to_time(supplier.recurrency_to))

    @api.depends('recurrency', 'recurrency_date', 'recurrency_from', 'recurrency_to', 'recurrency_monday',
                 'recurrency_tuesday', 'recurrency_wednesday', 'recurrency_thursday',
                 'recurrency_friday', 'recurrency_saturday', 'recurrency_sunday')
    def _compute_available_today(self):
        now = fields.Datetime.now().replace(tzinfo=pytz.UTC)

        for supplier in self:
            now = now.astimezone(pytz.timezone(supplier.tz))
            time_from = float_to_time(supplier.recurrency_from)
            time_to = float_to_time(supplier.recurrency_to)

            if supplier.recurrency == 'once':
                supplier.available_today = (supplier.reccurrency_date_from <= now <= supplier.reccurrency_date_to)
            else:
                fieldname = 'recurrency_%s' % (WEEKDAY_TO_NAME[now.weekday()])
                supplier.available_today = supplier[fieldname] and (time_from <= now.time() <= time_to)

    def _search_available_today(self, operator, value):
        if (not operator in ['=', '!=']) or (not value in [True, False]):
            return []

        searching_for_true = (operator == '=' and value) or (operator == '!=' and not value)
        now = fields.Datetime.now()
        float_now = time_to_float(now.time())
        fieldname = 'recurrency_%s' % (WEEKDAY_TO_NAME[now.weekday()])

        if searching_for_true:
            specific = expression.AND([
                [('recurrency', '=', 'once')],
                [('recurrency_date_from', '<=', now)],
                [('recurrency_date_to', '>=', now)]
            ])
        else:
            specific = expression.AND([
                [('recurrency', '=', 'once')],
                expression.OR([
                    [('recurrency_date_from', '>=', now)],
                    [('recurrency_date_to', '<=', now)]
                ])
            ])

        recurrence = expression.AND([
            [(fieldname, operator, value)],
            [('recurrency_from', '<=' if searching_for_true else '>=', float_now)],
            [('recurrency_to', '>=' if searching_for_true else '<=', float_now)]
        ])

        return expression.OR([specific, recurrence])
