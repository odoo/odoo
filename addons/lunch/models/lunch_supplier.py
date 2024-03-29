# Part of Odoo. See LICENSE file for full copyright and licensing details.

import math
import pytz

from collections import defaultdict
from datetime import datetime, time, timedelta
from textwrap import dedent

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.osv import expression
from odoo.tools import float_round

from odoo.addons.base.models.res_partner import _tz_get


WEEKDAY_TO_NAME = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
CRON_DEPENDS = {'name', 'active', 'send_by', 'automatic_email_time', 'moment', 'tz'}

def float_to_time(hours, moment='am'):
    """ Convert a number of hours into a time object. """
    if hours == 12.0 and moment == 'pm':
        return time.max
    fractional, integral = math.modf(hours)
    if moment == 'pm':
        integral += 12
    return time(int(integral), int(float_round(60 * fractional, precision_digits=0)), 0)

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
    cron_id = fields.Many2one('ir.cron', ondelete='cascade', required=True, readonly=True)

    mon = fields.Boolean(default=True)
    tue = fields.Boolean(default=True)
    wed = fields.Boolean(default=True)
    thu = fields.Boolean(default=True)
    fri = fields.Boolean(default=True)
    sat = fields.Boolean()
    sun = fields.Boolean()

    recurrency_end_date = fields.Date('Until', help="This field is used in order to ")

    available_location_ids = fields.Many2many('lunch.location', string='Location')
    available_today = fields.Boolean('This is True when if the supplier is available today',
                                     compute='_compute_available_today', search='_search_available_today')
    order_deadline_passed = fields.Boolean(compute='_compute_order_deadline_passed')

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

    topping_label_1 = fields.Char('Extra 1 Label', required=True, default='Extras')
    topping_label_2 = fields.Char('Extra 2 Label', required=True, default='Beverages')
    topping_label_3 = fields.Char('Extra 3 Label', required=True, default='Extra Label 3')
    topping_ids_1 = fields.One2many('lunch.topping', 'supplier_id', domain=[('topping_category', '=', 1)])
    topping_ids_2 = fields.One2many('lunch.topping', 'supplier_id', domain=[('topping_category', '=', 2)])
    topping_ids_3 = fields.One2many('lunch.topping', 'supplier_id', domain=[('topping_category', '=', 3)])
    topping_quantity_1 = fields.Selection([
        ('0_more', 'None or More'),
        ('1_more', 'One or More'),
        ('1', 'Only One')], 'Extra 1 Quantity', default='0_more', required=True)
    topping_quantity_2 = fields.Selection([
        ('0_more', 'None or More'),
        ('1_more', 'One or More'),
        ('1', 'Only One')], 'Extra 2 Quantity', default='0_more', required=True)
    topping_quantity_3 = fields.Selection([
        ('0_more', 'None or More'),
        ('1_more', 'One or More'),
        ('1', 'Only One')], 'Extra 3 Quantity', default='0_more', required=True)

    show_order_button = fields.Boolean(compute='_compute_buttons')
    show_confirm_button = fields.Boolean(compute='_compute_buttons')

    _sql_constraints = [
        ('automatic_email_time_range',
         'CHECK(automatic_email_time >= 0 AND automatic_email_time <= 12)',
         'Automatic Email Sending Time should be between 0 and 12'),
    ]

    @api.depends('phone')
    def _compute_display_name(self):
        for supplier in self:
            if supplier.phone:
                supplier.display_name = f'{supplier.name} {supplier.phone}'
            else:
                supplier.display_name = supplier.name

    def _sync_cron(self):
        for supplier in self:
            supplier = supplier.with_context(tz=supplier.tz)

            sendat_tz = pytz.timezone(supplier.tz).localize(datetime.combine(
                fields.Date.context_today(supplier),
                float_to_time(supplier.automatic_email_time, supplier.moment)))
            cron = supplier.cron_id.sudo()
            lc = cron.lastcall
            if ((
                lc and sendat_tz.date() <= fields.Datetime.context_timestamp(supplier, lc).date()
            ) or (
                not lc and sendat_tz <= fields.Datetime.context_timestamp(supplier, fields.Datetime.now())
            )):
                sendat_tz += timedelta(days=1)
            sendat_utc = sendat_tz.astimezone(pytz.UTC).replace(tzinfo=None)

            cron.active = supplier.active and supplier.send_by == 'mail'
            cron.name = f"Lunch: send automatic email to {supplier.name}"
            cron.nextcall = sendat_utc
            cron.code = dedent(f"""\
                # This cron is dynamically controlled by {self._description}.
                # Do NOT modify this cron, modify the related record instead.
                env['{self._name}'].browse([{supplier.id}])._send_auto_email()""")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            for topping in vals.get('topping_ids_2', []):
                topping[2].update({'topping_category': 2})
            for topping in vals.get('topping_ids_3', []):
                topping[2].update({'topping_category': 3})
        crons = self.env['ir.cron'].sudo().create([
            {
                'user_id': self.env.ref('base.user_root').id,
                'active': False,
                'interval_type': 'days',
                'interval_number': 1,
                'numbercall': -1,
                'doall': False,
                'name': "Lunch: send automatic email",
                'model_id': self.env['ir.model']._get_id(self._name),
                'state': 'code',
                'code': "",
            }
            for _ in range(len(vals_list))
        ])
        self.env['ir.model.data'].sudo().create([{
            'name': f'lunch_supplier_cron_sa_{cron.ir_actions_server_id.id}',
            'module': 'lunch',
            'res_id': cron.ir_actions_server_id.id,
            'model': 'ir.actions.server',
            # noupdate is set to true to avoid to delete record at module update
            'noupdate': True,
        } for cron in crons])
        for vals, cron in zip(vals_list, crons):
            vals['cron_id'] = cron.id

        suppliers = super().create(vals_list)
        suppliers._sync_cron()
        return suppliers

    def write(self, values):
        for topping in values.get('topping_ids_2', []):
            topping_values = topping[2]
            if topping_values:
                topping_values.update({'topping_category': 2})
        for topping in values.get('topping_ids_3', []):
            topping_values = topping[2]
            if topping_values:
                topping_values.update({'topping_category': 3})
        if values.get('company_id'):
            self.env['lunch.order'].search([('supplier_id', 'in', self.ids)]).write({'company_id': values['company_id']})
        res = super().write(values)
        if not CRON_DEPENDS.isdisjoint(values):
            # flush automatic_email_time field to call _sql_constraints
            if 'automatic_email_time' in values:
                self.flush_model(['automatic_email_time'])
            self._sync_cron()
        return res

    def unlink(self):
        crons = self.cron_id.sudo()
        server_actions = crons.ir_actions_server_id
        res = super().unlink()
        crons.unlink()
        server_actions.unlink()
        return res

    def toggle_active(self):
        """ Archiving related lunch product """
        res = super().toggle_active()
        active_suppliers = self.filtered(lambda s: s.active)
        inactive_suppliers = self - active_suppliers
        Product = self.env['lunch.product'].with_context(active_test=False)
        Product.search([('supplier_id', 'in', active_suppliers.ids)]).write({'active': True})
        Product.search([('supplier_id', 'in', inactive_suppliers.ids)]).write({'active': False})
        return res

    def _get_current_orders(self, state='ordered'):
        """ Returns today's orders """
        available_today = self.filtered('available_today')
        if not available_today:
            return self.env['lunch.order']

        orders = self.env['lunch.order'].search([
            ('supplier_id', 'in', available_today.ids),
            ('state', '=', state),
            ('date', '=', fields.Date.context_today(self.with_context(tz=self.tz))),
        ], order="user_id, product_id")
        return orders

    def _send_auto_email(self):
        """ Send an email to the supplier with the order of the day """
        # Called daily by cron
        self.ensure_one()

        if not self.available_today:
            return

        if self.send_by != 'mail':
            raise UserError(_("Cannot send an email to this supplier!"))

        orders = self._get_current_orders()
        if not orders:
            return

        order = {
            'company_name': orders[0].company_id.name,
            'currency_id': orders[0].currency_id.id,
            'supplier_id': self.partner_id.id,
            'supplier_name': self.name,
            'email_from': self.responsible_id.email_formatted,
            'amount_total': sum(order.price for order in orders),
        }

        sites = orders.mapped('user_id.last_lunch_location_id').sorted(lambda x: x.name)
        orders_per_site = orders.sorted(lambda x: x.user_id.last_lunch_location_id.id)

        email_orders = [{
            'product': order.product_id.name,
            'note': order.note,
            'quantity': order.quantity,
            'price': order.price,
            'toppings': order.display_toppings,
            'username': order.user_id.name,
            'site': order.user_id.last_lunch_location_id.name,
        } for order in orders_per_site]

        email_sites = [{
            'name': site.name,
            'address': site.address,
        } for site in sites]

        self.env.ref('lunch.lunch_order_mail_supplier').with_context(
            order=order, lines=email_orders, sites=email_sites
        ).send_mail(self.id)

        orders.action_send()

    @api.depends('recurrency_end_date', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun')
    def _compute_available_today(self):
        now = fields.Datetime.now().replace(tzinfo=pytz.UTC)

        for supplier in self:
            now = now.astimezone(pytz.timezone(supplier.tz))

            supplier.available_today = supplier._available_on_date(now)

    def _available_on_date(self, date):
        self.ensure_one()

        fieldname = WEEKDAY_TO_NAME[date.weekday()]
        return not (self.recurrency_end_date and date.date() >= self.recurrency_end_date) and self[fieldname]

    @api.depends('available_today', 'automatic_email_time', 'send_by')
    def _compute_order_deadline_passed(self):
        now = fields.Datetime.now().replace(tzinfo=pytz.UTC)

        for supplier in self:
            if supplier.send_by == 'mail':
                now = now.astimezone(pytz.timezone(supplier.tz))
                email_time = pytz.timezone(supplier.tz).localize(datetime.combine(
                    fields.Date.context_today(supplier),
                    float_to_time(supplier.automatic_email_time, supplier.moment)))
                supplier.order_deadline_passed = supplier.available_today and now > email_time
            else:
                supplier.order_deadline_passed = not supplier.available_today

    def _search_available_today(self, operator, value):
        if (not operator in ['=', '!=']) or (not value in [True, False]):
            return []

        searching_for_true = (operator == '=' and value) or (operator == '!=' and not value)

        now = fields.Datetime.now().replace(tzinfo=pytz.UTC).astimezone(pytz.timezone(self.env.user.tz or 'UTC'))
        fieldname = WEEKDAY_TO_NAME[now.weekday()]

        recurrency_domain = expression.OR([
            [('recurrency_end_date', '=', False)],
            [('recurrency_end_date', '>' if searching_for_true else '<', now)]
        ])

        return expression.AND([
            recurrency_domain,
            [(fieldname, operator, value)]
        ])

    def _compute_buttons(self):
        self.env.cr.execute("""
            SELECT supplier_id, state, COUNT(*)
              FROM lunch_order
             WHERE supplier_id IN %s
               AND state in ('ordered', 'sent')
               AND date = %s
               AND active
          GROUP BY supplier_id, state
        """, (tuple(self.ids), fields.Date.context_today(self)))
        supplier_orders = defaultdict(dict)
        for order in self.env.cr.fetchall():
            supplier_orders[order[0]][order[1]] = order[2]
        for supplier in self:
            supplier.show_order_button = supplier_orders[supplier.id].get('ordered', False)
            supplier.show_confirm_button = supplier_orders[supplier.id].get('sent', False)

    def action_send_orders(self):
        no_auto_mail = self.filtered(lambda s: s.send_by != 'mail')

        for supplier in self - no_auto_mail:
            supplier._send_auto_email()
        orders = no_auto_mail._get_current_orders()
        orders.action_send()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'message': _('The orders have been sent!'),
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }

    def action_confirm_orders(self):
        orders = self._get_current_orders(state='sent')
        orders.action_confirm()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'message': _('The orders have been confirmed!'),
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }
