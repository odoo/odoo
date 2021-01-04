# -*- coding: utf-8 -*-
###################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#    Copyright (C) 2019-TODAY Cybrosys Technologies (<https://www.cybrosys.com>).
#
#    Author: AVINASH NK(<https://www.cybrosys.com>)
#
#    This program is free software: you can modify
#    it under the terms of the GNU Affero General Public License (AGPL) as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
###################################################################################

from datetime import date, datetime, timedelta
from odoo import models, fields, api
from odoo.tools.translate import _
from odoo.exceptions import UserError, ValidationError


class PartnerSalon(models.Model):
    _inherit = 'res.partner'

    partner_salon = fields.Boolean(string="Is a Salon Partner")


class SequenceUpdaterSalon(models.Model):
    _name = 'salon.sequence.updater'

    sequence_salon = fields.Char(string="Salon Sequence")


class UserSalon(models.Model):
    _inherit = 'res.users'

    user_salon_active = fields.Boolean(string="Active Salon Users")


class SalonChair(models.Model):
    _name = 'salon.chair'

    name = fields.Char(string="Chair", required=True,
                       default=lambda self: self.env['salon.sequence.updater'].browse(1).sequence_salon or "Chair-1")
    number_of_orders = fields.Integer(string="No.of Orders")
    collection_today = fields.Float(string="Today's Collection")
    user_of_chair = fields.Many2one('res.users', string="User", readonly=True,
                                    help="You can select the user from the Users Tab."
                                         "Last user from the Users Tab will be selected as the Current User.")
    date = fields.Datetime(string="Date", readonly=True)
    user_line = fields.One2many('salon.chair.user', 'salon_chair', string="Users")
    total_time_taken_chair = fields.Float(string="Time Reserved(Hrs)")
    active_booking_chairs = fields.Boolean(string="Active booking chairs")
    chair_created_user = fields.Integer(string="Salon Chair Created User",
                                        default=lambda self: self._uid)

    @api.model
    def create(self, values):
        sequence_code = 'chair.sequence'
        sequence_number = self.env['ir.sequence'].next_by_code(sequence_code)
        self.env['salon.sequence.updater'].browse(1).write({'sequence_salon': sequence_number})
        if 'user_line' in values.keys():
            if values['user_line']:
                date_changer = []
                for elements in values['user_line']:
                    date_changer.append(elements[2]['start_date'])
                number = 0
                for elements in values['user_line']:
                    number += 1
                    if len(values['user_line']) == number:
                        break
                    elements[2]['end_date'] = date_changer[number]
                values['user_of_chair'] = values['user_line'][len((values['user_line'])) - 1][2]['user_id']
                values['date'] = values['user_line'][len((values['user_line'])) - 1][2]['start_date']
        return super(SalonChair, self).create(values)

    def write(self, values):
        if 'user_line' in values.keys():
            if values['user_line']:
                date_changer = []
                for elements in values['user_line']:
                    if str(elements[1]).startswith('v'):
                        date_changer.append(elements[2]['start_date'])
                number = 0
                num = 0
                for records in self.user_line:
                    if records.end_date is False:
                        if date_changer:
                            records.end_date = date_changer[0]
                for elements in values['user_line']:
                    number += 1
                    if elements[2] is not False:
                        num += 1
                        if len(values['user_line']) == number:
                            break
                        elements[2]['end_date'] = date_changer[num]
                values['user_of_chair'] = values['user_line'][len((values['user_line'])) - 1][2]['user_id']
                values['date'] = values['user_line'][len((values['user_line'])) - 1][2]['start_date']
        return super(SalonChair, self).write(values)

    def collection_today_updater(self):
        salon_chair = self.env['salon.chair']
        for values in self.search([]):
            chair_obj = salon_chair.browse(values.ids)
            invoiced_records = chair_obj.env['salon.order'].search([('stage_id', 'in', [3, 4]),
                                                                    ('chair_id', '=', chair_obj.id)])
            total = 0
            for rows in invoiced_records:
                invoiced_date = str(rows.date)
                invoiced_date = invoiced_date[0:10]
                if invoiced_date == str(date.today()):
                    total = total + rows.price_subtotal
            chair_obj.collection_today = total


class SalonChairUserLines(models.Model):
    _name = 'salon.chair.user'

    read_only_checker = fields.Boolean(string="Checker", default=False)
    user_id = fields.Many2one('res.users', string="User", required=True)
    start_date = fields.Datetime(string="Start Date", default=datetime.today(), required=True)
    end_date = fields.Datetime(string="End Date", readonly=True, default=False)
    salon_chair = fields.Many2one('salon.chair', string="Chair", required=True, ondelete='cascade',
                                  index=True, copy=False)

    @api.model
    def create(self, val):
        chairs = self.env['salon.chair'].search([])
        all_active_users = []
        for records in chairs:
            if records.user_of_chair:
                all_active_users.append(records.user_of_chair.id)
                records.user_of_chair.write({'user_salon_active': True})
        users = self.env['res.users'].search([('id', 'not in', all_active_users)])
        for records in users:
            records.write({'user_salon_active': False})
        val['read_only_checker'] = True
        return super(SalonChairUserLines, self).create(val)


class SalonOrder(models.Model):
    _name = 'salon.order'

    @api.depends('order_line.price_subtotal')
    def sub_total_update(self):
        for order in self:
            amount_untaxed = 0.0
            total_time_taken = 0.0
            for line in order.order_line:
                amount_untaxed += line.price_subtotal
                total_time_taken += line.time_taken
        self.price_subtotal = amount_untaxed
        time_takes = total_time_taken
        hours = int(time_takes)
        minutes = (time_takes - hours) * 60
        start_time_store = datetime.strptime(str(self.start_time).split(".")[0], "%Y-%m-%d %H:%M:%S")
        self.write({'end_time': start_time_store + timedelta(hours=hours, minutes=minutes),
                    'time_taken_total': total_time_taken})
        if self.end_time:
            self.write({'end_time_only': str(self.end_time)[11:16]})
        if self.start_time:
            salon_start_time = str(self.start_time)
            salon_start_time_date = salon_start_time[0:10]
            self.write({'start_date_only': salon_start_time_date})
            self.write({'start_time_only': str(self.start_time)[11:16]})

    name = fields.Char(string='Salon', required=True, copy=False, readonly=True,
                       default='Draft Salon Order')
    start_time = fields.Datetime(string="Start time", default=datetime.now(), required=True)
    end_time = fields.Datetime(string="End time")
    date = fields.Datetime(string="Date", required=True, default=datetime.now())
    color = fields.Integer(string="Colour", default=6)
    partner_id = fields.Many2one('res.partner', string="Customer", required=False,
                                 help="If the customer is a regular customer, "
                                      "then you can add the customer in your database")
    customer_name = fields.Char(string="Name", required=True)
    amount = fields.Float(string="Amount")
    chair_id = fields.Many2one('salon.chair', string="Chair", required=True)
    price_subtotal = fields.Float(string='Total', compute='sub_total_update', readonly=True, store=True)
    time_taken_total = fields.Float(string="Total time taken")
    note = fields.Text('Terms and conditions')
    order_line = fields.One2many('salon.order.lines', 'salon_order', string="Order Lines")
    stage_id = fields.Many2one('salon.stages', string="Stages", default=1, group_expand='_read_group_stage_ids')
    inv_stage_identifier = fields.Boolean(string="Stage Identifier")
    invoice_number = fields.Integer(string="Invoice Number")
    validation_controller = fields.Boolean(string="Validation controller", default=False)
    start_date_only = fields.Date(string="Date Only")
    booking_identifier = fields.Boolean(string="Booking Identifier")
    start_time_only = fields.Char(string="Start Time Only")
    end_time_only = fields.Char(string="End Time Only")
    chair_user = fields.Many2one('res.users', string="Chair User")
    salon_order_created_user = fields.Integer(string="Salon Order Created User",
                                              default=lambda self: self._uid)

    @api.onchange('start_time')
    def start_date_change(self):
        salon_start_time = str(self.start_time)
        salon_start_time_date = salon_start_time[0:10]
        self.write({'start_date_only': salon_start_time_date})

    count = fields.Integer(string='Delivery Orders',
                           compute='_compute_invoice_saloon_ids')

    def _compute_invoice_saloon_ids(self):
        """getting saloon invoice count"""
        for orders in self:
            orders.count = self.env['account.move']. \
                search_count([('invoice_origin', '=', self.name)])


            # if orders.count != 0:
            #     orders.inv_stage_identifier = True
            #     orders.stage_id = 3

    def action_view_invoice_salon(self):

        return {
            'name': 'Invoices',
            'domain': [('invoice_origin', '=', self.name)],
            'res_model': 'account.move',
            'view_id': False,
            'view_mode': 'tree,form',
            'type': 'ir.actions.act_window',
        }

    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        stage_ids = self.env['salon.stages'].search([])
        return stage_ids

    def write(self, values):
        if 'stage_id' in values.keys():
            if self.stage_id.id == 3 and values['stage_id'] != 4:
                raise ValidationError(_("You can't perform that move !"))
            if self.stage_id.id == 1 and values['stage_id'] not in [2, 5]:
                raise ValidationError(_("You can't perform that move!"))
            if self.stage_id.id == 4:
                raise ValidationError(_("You can't move a salon order from closed stage !"))
            if self.stage_id.id == 5:
                raise ValidationError(_("You can't move a salon order from cancel stage !"))
            if self.stage_id.id == 2 and (values['stage_id'] == 1 or values['stage_id'] == 4):
                raise ValidationError(_("You can't perform that move !"))
            if self.stage_id.id == 2 and values['stage_id'] == 3 and self.inv_stage_identifier is False:
                self.salon_invoice_create()

        if 'stage_id' in values.keys() and self.name == "Draft Salon Order":
            if values['stage_id'] == 2:
                self.salon_confirm()
        return super(SalonOrder, self).write(values)

    def salon_confirm(self):
        sequence_code = 'salon.order.sequence'
        order_date = str(self.date)
        order_date = order_date[0:10]
        self.name = self.env['ir.sequence'].with_context(ir_sequence_date=order_date).next_by_code(sequence_code)
        if self.partner_id:
            self.partner_id.partner_salon = True
        self.stage_id = 2
        self.chair_id.number_of_orders = len(self.env['salon.order'].search([("chair_id", "=", self.chair_id.id),
                                                                             ("stage_id", "in", [2, 3])]))
        self.chair_id.total_time_taken_chair = (self.chair_id.total_time_taken_chair + self.time_taken_total)
        self.chair_user = self.chair_id.user_of_chair

    def salon_validate(self):
        self.validation_controller = True

    def salon_close(self):

        self.stage_id = 4
        self.chair_id.number_of_orders = len(self.env['salon.order'].search([("chair_id", "=", self.chair_id.id),
                                                                             ("stage_id", "in", [2, 3])]))
        self.chair_id.total_time_taken_chair = (self.chair_id.total_time_taken_chair - self.time_taken_total)

    def salon_cancel(self):
        self.stage_id = 5
        self.chair_id.number_of_orders = len(self.env['salon.order'].search([("chair_id", "=", self.chair_id.id),
                                                                             ("stage_id", "in", [2, 3])]))
        if self.stage_id.id != 1:
            self.chair_id.total_time_taken_chair = (self.chair_id.total_time_taken_chair - self.time_taken_total)

    def button_total_update(self):
        for order in self:
            amount_untaxed = 0.0
            for line in order.order_line:
                amount_untaxed += line.price_subtotal
            order.price_subtotal = amount_untaxed


    @api.onchange('chair_id')
    def onchange_chair(self):
        if 'active_id' in self._context.keys():
            self.chair_id = self._context['active_id']

    def salon_invoice_create(self):
        if self.partner_id:
            supplier = self.partner_id
        else:
            supplier = self.partner_id.search([("name", "=", "Salon Default Customer")])
        lines = []
        product_id = self.env['product.product'].search([("name", "=", "Salon Service")])
        for records in self.order_line:
            if product_id.property_account_income_id.id:
                income_account = product_id.property_account_income_id.id
            elif product_id.categ_id.property_account_income_categ_id.id:
                income_account = product_id.categ_id.property_account_income_categ_id.id
            else:
                raise UserError(_('Please define income account for this product: "%s" (id:%d).') % (product_id.name,
                                                                                                     product_id.id))

            value = (0, 0, {
                        'name': records.service_id.name,
                        'account_id': income_account,
                        'price_unit': records.price,
                        'quantity': 1,
                        'product_id': product_id.id,
                    })
            lines.append(value)

        invoice_line = {
            'move_type': 'out_invoice',
            'partner_id': supplier.id,
            'invoice_user_id': self.env.user.id,
            'invoice_origin': self.name,
            'invoice_line_ids': lines,
        }
        inv = self.env['account.move'].create(invoice_line)


        imd = self.env['ir.model.data']

        action = imd.xmlid_to_object('account.action_move_out_invoice_type')
        result = {
            'name': action.name,
            'type': 'ir.actions.act_window',
            'views': [[False, 'form']],
            'target': 'current',
            'res_id':inv.id,
            'res_model': 'account.move',
        }

        self.inv_stage_identifier = True
        self.stage_id = 3
        invoiced_records = self.env['salon.order'].search([('stage_id', 'in', [3, 4]),
                                                           ('chair_id', '=', self.chair_id.id)])
        total = 0
        for rows in invoiced_records:
            invoiced_date = str(rows.date)
            invoiced_date = invoiced_date[0:10]
            if invoiced_date == str(date.today()):
                total = total + rows.price_subtotal
        self.chair_id.collection_today = total
        self.chair_id.number_of_orders = len(self.env['salon.order'].search([("chair_id", "=", self.chair_id.id),
                                                                             ("stage_id", "in", [2, 3])]))

        return result

    def unlink(self):
        for order in self:
            if order.stage_id.id == 3 or order.stage_id.id == 4:
                raise UserError(_("You can't delete an invoiced salon order!"))
        return super(SalonOrder, self).unlink()


class SalonServices(models.Model):
    _name = 'salon.service'

    name = fields.Char(string="Name")
    price = fields.Float(string="Price")
    time_taken = fields.Float(string="Time Taken", help="Approximate time taken for this service in Hours")


class SalonOrderLine(models.Model):
    _name = 'salon.order.lines'

    service_id = fields.Many2one('salon.service', string="Service")
    price = fields.Float(string="Price")
    salon_order = fields.Many2one('salon.order', string="Salon Order", required=True, ondelete='cascade',
                                  index=True, copy=False)
    price_subtotal = fields.Float(string='Subtotal')
    time_taken = fields.Float(string='Time Taken')

    @api.onchange('service_id')
    def onchange_service(self):
        self.price = self.service_id.price
        self.price_subtotal = self.service_id.price
        self.time_taken = self.service_id.time_taken

    @api.onchange('price')
    def onchange_price(self):
        self.price_subtotal = self.price

    @api.onchange('price_subtotal')
    def onchange_subtotal(self):
        self.price = self.price_subtotal
 

class SalonStages(models.Model):
    _name = 'salon.stages'
    _order = "sequence"

    name = fields.Char(string="Name", required=True, translate=True)
    sequence = fields.Integer('Sequence', default=1, help="Used to order stages. Lower is better.")
