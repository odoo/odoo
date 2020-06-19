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

def float_to_time(hours, moment='am', tz=None):
    """ Convert a number of hours into a time object. """
    if hours == 12.0 and moment == 'pm':
        return time.max
    fractional, integral = math.modf(hours)
    if moment == 'pm':
        integral += 12
    res = time(int(integral), int(float_round(60 * fractional, precision_digits=0)), 0)
    if tz:
        res = res.replace(tzinfo=pytz.timezone(tz))
    return res

def time_to_float(t):
    return float_round(t.hour + t.minute/60 + t.second/3600, precision_digits=2)

class LunchSupplier(models.Model):
    _name = 'lunch.supplier'
    _description = 'Lunch Supplier'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    partner_id = fields.Many2one('res.partner', string='Vendor', required=True)

    name = fields.Char('Name', related='partner_id.name', readonly=False)

    email = fields.Char(related='partner_id.email', readonly=False)
    email_formatted = fields.Char(related='partner_id.email_formatted', readonly=True)
    phone = fields.Char(related='partner_id.phone', readonly=False)
    street = fields.Char(related='partner_id.street', readonly=False)
    street2 = fields.Char(related='partner_id.street2', readonly=False)
    zip_code = fields.Char(related='partner_id.zip', readonly=False)
    city = fields.Char(related='partner_id.city', readonly=False)
    state_id = fields.Many2one("res.country.state", related='partner_id.state_id', readonly=False)
    country_id = fields.Many2one('res.country', related='partner_id.country_id', readonly=False)
    company_id = fields.Many2one('res.company', related='partner_id.company_id', readonly=False, store=True)

    responsible_id = fields.Many2one('res.users', string="Responsible", domain=lambda self: [('groups_id', 'in', self.env.ref('lunch.group_lunch_manager').id)],
                                     default=lambda self: self.env.user,
                                     help="The responsible is the person that will order lunch for everyone. It will be used as the 'from' when sending the automatic email.")

    send_by = fields.Selection([
        ('phone', 'Phone'),
        ('mail', 'Email'),
    ], 'Send Order By', default='phone')
    automatic_email_time = fields.Float('Order Time', default=12.0, required=True)

    recurrency_monday = fields.Boolean('Monday', default=True)
    recurrency_tuesday = fields.Boolean('Tuesday', default=True)
    recurrency_wednesday = fields.Boolean('Wednesday', default=True)
    recurrency_thursday = fields.Boolean('Thursday', default=True)
    recurrency_friday = fields.Boolean('Friday', default=True)
    recurrency_saturday = fields.Boolean('Saturday')
    recurrency_sunday = fields.Boolean('Sunday')

    recurrency_end_date = fields.Date('Until', help="This field is used in order to ")

    available_location_ids = fields.Many2many('lunch.location', string='Location')
    available_today = fields.Boolean('This is True when if the supplier is available today',
                                     compute='_compute_available_today', search='_search_available_today')

    tz = fields.Selection(_tz_get, string='Timezone', required=True, default=lambda self: self.env.user.tz or 'UTC')

    active = fields.Boolean(default=True)

    moment = fields.Selection([
        ('am', 'AM'),
        ('pm', 'PM'),
    ], default='am', required=True)

    delivery = fields.Selection([
        ('delivery', 'Delivery'),
        ('no_delivery', 'No Delivery')
    ], default='no_delivery')

    _sql_constraints = [
        ('automatic_email_time_range',
         'CHECK(automatic_email_time >= 0 AND automatic_email_time <= 12)',
         'Automatic Email Sending Time should be between 0 and 12'),
    ]

    def name_get(self):
        res = []
        for supplier in self:
            if supplier.phone:
                res.append((supplier.id, '%s %s' % (supplier.name, supplier.phone)))
            else:
                res.append((supplier.id, supplier.name))
        return res

    @api.model
    def _auto_email_send(self):
        """
            This method is called every 20 minutes via a cron.
            Its job is simply to get all the orders made for each supplier and send an email
            automatically to the supplier if the supplier is configured for it and we are ready
            to send it (usually at 11am or so)
        """
        records = self.search([('send_by', '=', 'mail')])

        for supplier in records:
            send_at = datetime.combine(fields.Date.today(),
                                       float_to_time(supplier.automatic_email_time, supplier.moment, supplier.tz)).astimezone(pytz.UTC).replace(tzinfo=None)
            if supplier.available_today and fields.Datetime.now() > send_at:
                lines = self.env['lunch.order'].search([('supplier_id', '=', supplier.id),
                                                             ('state', '=', 'ordered'), ('date', '=', fields.Date.today())])

                if lines:
                    order = {
                        'company_name': lines[0].company_id.name,
                        'currency_id': lines[0].currency_id.id,
                        'supplier_id': supplier.partner_id.id,
                        'supplier_name': supplier.name,
                        'email_from': supplier.responsible_id.email_formatted,
                    }

                    _lines = [{
                        'product': line.product_id.name,
                        'note': line.note,
                        'quantity': line.quantity,
                        'price': line.price,
                        'toppings': line.display_toppings,
                        'username': line.user_id.name,
                    } for line in lines]

                    order['amount_total'] = sum(line.price for line in lines)

                    self.env.ref('lunch.lunch_order_mail_supplier').with_context(order=order, lines=_lines).send_mail(supplier.id)

                    lines.action_confirm()

    @api.depends('recurrency_end_date', 'recurrency_monday', 'recurrency_tuesday',
                 'recurrency_wednesday', 'recurrency_thursday', 'recurrency_friday',
                 'recurrency_saturday', 'recurrency_sunday')
    def _compute_available_today(self):
        now = fields.Datetime.now().replace(tzinfo=pytz.UTC)

        for supplier in self:
            now = now.astimezone(pytz.timezone(supplier.tz))

            if supplier.recurrency_end_date and now.date() >= supplier.recurrency_end_date:
                supplier.available_today = False
            else:
                fieldname = 'recurrency_%s' % (WEEKDAY_TO_NAME[now.weekday()])
                supplier.available_today = supplier[fieldname]

    def _search_available_today(self, operator, value):
        if (not operator in ['=', '!=']) or (not value in [True, False]):
            return []

        searching_for_true = (operator == '=' and value) or (operator == '!=' and not value)

        now = fields.Datetime.now().replace(tzinfo=pytz.UTC).astimezone(pytz.timezone(self.env.user.tz or 'UTC'))
        fieldname = 'recurrency_%s' % (WEEKDAY_TO_NAME[now.weekday()])

        recurrency_domain = expression.OR([
            [('recurrency_end_date', '=', False)],
            [('recurrency_end_date', '>' if searching_for_true else '<', now)]
        ])

        return expression.AND([
            recurrency_domain,
            [(fieldname, operator, value)]
        ])
