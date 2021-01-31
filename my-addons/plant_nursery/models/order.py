# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import random

from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import email_split, email_split_and_format


class Order(models.Model):
    _name = 'nursery.order'
    _description = 'Nursery Order'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'rating.mixin', 'utm.mixin']

    name = fields.Char(
        'Reference', default=lambda self: _('New'), required=True, states={'draft': [('readonly', False)]})
    user_id = fields.Many2one(
        'res.users', string='Responsible',
        index=True, required=True,
        default=lambda self: self.env.user)
    date_open = fields.Date(
        'Confirmation date', readonly=True)
    customer_id = fields.Many2one(
        "nursery.customer",
        string='Customer',
        index=True, required=True)
    partner_id = fields.Many2one(
        'res.partner', string='Customer Address', related='customer_id.partner_id')
    line_ids = fields.One2many(
        'nursery.order.line', 'order_id', string='Order Lines')
    amount_total = fields.Monetary(
        string='Amount', compute='_compute_amount_total',
        currency_field='currency_id', store=True)
    company_id = fields.Many2one(
        'res.company', string='Company', related='user_id.company_id',
        readonly=True, store=True)
    currency_id = fields.Many2one(
        'res.currency', string='Currency', related='company_id.currency_id',
        readonly=True, required=True)
    category_id = fields.Many2one('nursery.plant.category', string='Category')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('open', 'Open'),
        ('done', 'Done'),
        ('cancel', 'Canceled'),
    ], default='draft', index=True, group_expand="_expand_states")
    last_modification = fields.Datetime(readonly=True)

    @api.depends('line_ids.price')
    def _compute_amount_total(self):
        for order in self:
            order.amount_total = sum(order.mapped('line_ids.price'))

    def _compute_access_url(self):
        super(Order, self)._compute_access_url()
        for order in self:
            order.access_url = '/my/order/%s' % order.id

    def _compute_access_warning(self):
        super(Order, self)._compute_access_warning()
        for order in self:
            if order.category_id.internal:
                order.access_warning = _('You cannot share this order. It is internal and therefore private.')

    @api.onchange('category_id')
    def _onchange_category_id(self):
        if self.category_id.order_user_id:
            self.user_id = self.category_id.order_user_id

    def action_confirm(self):
        if self.state != 'draft':
            return
        for line in self.line_ids:
            line.plant_id.number_in_stock -= 1
        self.activity_feedback(['mail.mail_activity_data_todo'])
        return self.write({
            'state': 'open',
            'date_open': fields.Datetime.now(),
        })

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            if 'company_id' in vals:
                vals['name'] = self.env['ir.sequence'].with_context(force_company=vals['company_id']).next_by_code('plant.order') or _('New')
            else:
                vals['name'] = self.env['ir.sequence'].next_by_code('plant.order') or _('New')
        res = super(Order, self).create(vals)
        res.activity_schedule(
            'mail.mail_activity_data_todo',
            user_id=res.user_id.id,
            date_deadline=fields.Date.today() + relativedelta(days=1),
            summary=_('Pack the order'))
        return res

    def write(self, values):
        # helper to "YYYY-MM-DD"
        values['last_modification'] = fields.Datetime.now()

        return super(Order, self).write(values)

    def unlink(self):
        # self is a recordset
        for order in self:
            if order.state == 'confirm':
                raise UserError("You can not delete confirmed orders")

        return super(Order, self).unlink()

    def _expand_states(self, states, domain, order):
        return [key for key, val in type(self).state.selection]

    def action_view_ratings(self):
        action = self.env.ref('plant_nursery.rating_rating_action_nursery').read()[0]
        action['domain'] = [('res_id', 'in', self.ids), ('res_model', '=', 'nursery.order')]
        return action

    def action_send_rating(self):
        rating_template = self.env.ref('plant_nursery.mail_template_plant_order_rating')
        for order in self:
            order.rating_send_request(rating_template, force_send=True, notif_layout='mail.mail_notification_light')

    def rating_get_partner_id(self):
        if self.customer_id.partner_id:
            return self.customer_id.partner_id
        return self.env['res.partner']

    def _rating_get_parent_field_name(self):
        return 'category_id'

    def message_new(self, msg_dict, custom_values=None):
        if custom_values is None:
            custom_values = {}

        # print(msg_dict.get('email_from'), msg_dict.get('author_id'), msg_dict.get('to'), msg_dict.get('recipients'), msg_dict.get('partner_ids'))
        category = custom_values.pop('category_id', False)
        domain = [('category_id', '=', category)] if category else []

        # find or create customer
        email = email_split(msg_dict.get('email_from', False))[0]
        name = email_split_and_format(msg_dict.get('email_from', False))[0]
        customer = self.env['nursery.customer'].find_or_create(email, name)

        # happy Xmas
        plants = self.env['nursery.plant'].search(domain)
        plant = self.env['nursery.plant'].browse([random.choice(plants.ids)])
        custom_values.update({
            'customer_id': customer.id,
            'line_ids': [(4, plant.id)],
        })
        if category:
            custom_values['category_id'] = category

        return super(Order, self).message_new(msg_dict, custom_values=custom_values)


class OrderLine(models.Model):
    _name = 'nursery.order.line'
    _description = 'Plant Order Line'
    _order = 'order_id DESC'
    _rec_name = 'order_id'

    order_id = fields.Many2one(
        'nursery.order', string='Order',
        index=True, ondelete='cascade', required=True)
    plant_id = fields.Many2one(
        'nursery.plant', string='Plant',
        index=True, ondelete='cascade', required=True)
    price = fields.Float('Price')

    @api.onchange('plant_id')
    def _onchange_plant_id(self):
        if self.plant_id:
            self.price = self.plant_id.price

    @api.model
    def create(self, values):
        if 'price' not in values:
            values['price'] = self.env['nursery.plant'].browse(values['plant_id']).price
        return super(OrderLine, self).create(values)
