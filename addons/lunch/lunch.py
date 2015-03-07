# -*- coding: utf-8 -*-

import datetime
from lxml import etree
from lxml.builder import E
from xml.sax.saxutils import escape

from openerp import models, fields, api, _

import logging
_logger = logging.getLogger(__name__)


class lunch_order(models.Model):

    """
    lunch order (contains one or more lunch order line(s))
    """
    _name = 'lunch.order'
    _description = 'Lunch Order'
    _order = 'date desc'

    @api.multi
    def add_preference(self, pref_id):
        """
        create a new order line based on the preference selected (pref_id)
        """
        self.ensure_one()
        OrderLine = self.env['lunch.order.line']
        pref = OrderLine.browse(pref_id)
        new_order_line = {
            'date': self.date,
            'user_id': self.env.uid,
            'product_id': pref.product_id.id,
            'note': pref.note,
            'order_id': self.id,
            'price': pref.product_id.price,
            'supplier': pref.product_id.supplier.id
        }
        return OrderLine.create(new_order_line)

    @api.model
    def _default_alerts_get(self):
        """
        get the alerts to display on the order form
        """
        alert_msg = [alert.get_alert_message()
                     for alert in self.env['lunch.alert'].search([]) if alert.get_alert_message()]
        return '\n'.join(alert_msg)

    def __getattr__(self, attr):
        """
        this method catch unexisting method call and if it starts with
        add_preference_'n' we execute the add_preference method with
        'n' as parameter
        """
        if attr.startswith('add_preference_'):
            try:
                pref_id = int(attr[15:])

                def specific_function(cr, uid, ids, context=None):
                    return self.add_preference(cr, uid, ids, pref_id, context=context)
                return specific_function
            except Exception, e:
                return _logger.warning('Wrong preferences', exc_info=True)
        return super(lunch_order, self).__getattr__(attr)

    @api.model
    def fields_view_get(self, view_id=None, view_type=False, toolbar=True):
        """
        Add preferences in the form view of order.line
        """
        res = super(lunch_order, self).fields_view_get(
            view_id=view_id, view_type=view_type, toolbar=True)
        if view_type == 'form':
            doc = etree.XML(res['arch'])
            preferences = self.order_line_ids.read_group([('user_id', '=', self.env.uid)], [
                                                         'product_id', 'category_id'], ['category_id'], lazy=False)
            # If there are no preference (it's the first time for the user)
            if not preferences:
                xml_start = E.div(
                    E.div({"class": "oe_inline oe_lunch_intro"},
                          E.h3(_("This is the first time you order a meal")),
                          E.p(_("Select a product and put your order comments on the note."),
                              {"class": "oe_grey"}),
                          E.p(_("Your favorite meals will be created based on your last orders."),
                              {"class": "oe_grey"}),
                          E.p(_("Don't forget the alerts displayed in the reddish area"),
                              {"class": "oe_grey"}),
                          )
                )
            # Else: the user already have preferences so we display them
            else:
                xml_start = E.div(*[E.div({"class": "oe_lunch_30pc"},
                                          E.h2(pref['category_id'][1]),
                                          *([
                                              E.div({"class": "oe_lunch_vignette"},
                                                    E.span({"class": "oe_lunch_button"},
                                                           E.button({"name": "add_preference_" + str(orderline.id),
                                                                     "class": "oe_link oe_i oe_button_plus",
                                                                     "type": "object",
                                                                     "string": "+"
                                                                     }),
                                                           E.button({"name": "add_preference_" + str(orderline.id),
                                                                     "class": "oe_link oe_button_add",
                                                                     "type": "object",
                                                                     "string": _("Add")
                                                                     })
                                                           ),
                                                    E.div({"class": "oe_group_text_button"},
                                                          E.div(escape(orderline.product_id.name) + str(" "),
                                                                {"class":
                                                                 "oe_lunch_text"},
                                                                E.span(str(orderline.product_id.price or 0.0) + str(" ") + self.env.user.company_id.currency_id.name or '',
                                                                       {"class":
                                                                        "oe_tag"}
                                                                       )
                                                                )
                                                          ),
                                                    E.div(escape(orderline.note or ''),
                                                          {"class": "oe_grey"}
                                                          )
                                                    ) for orderline in self.order_line_ids.search(pref['__domain'], limit=5, order='id desc')
                                          ])
                                          ) for pref in preferences])
            first_node = doc.xpath("//div[@name='preferences']")
            if first_node:
                first_node[0].append(xml_start)
            res['arch'] = etree.tostring(doc)
        return res

    user_id = fields.Many2one('res.users', 'User Name', required=True, readonly=True, states={
                              'new': [('readonly', False)]}, default=lambda self: self.env.uid)
    date = fields.Date('Date', required=True, readonly=True, states={
                       'new': [('readonly', False)]}, default=fields.Date.context_today)
    order_line_ids = fields.One2many('lunch.order.line', 'order_id', 'Products',
                                     ondelete="cascade", readonly=True, states={'new': [('readonly', False)]},
                                     copy=True)
    total = fields.Float(compute='_compute_total', string="Total", store=True)

    @api.multi
    @api.depends('order_line_ids')
    def _compute_total(self):
        """
        get and sum the order lines' price
        """
        for order in self:
            order.total = sum(
                order_line.price for order_line in order.order_line_ids)

    state = fields.Selection([('new', 'New'),
                              ('confirmed', 'Confirmed'),
                              ('cancelled', 'Cancelled'),
                              ('partially', 'Partially Confirmed')], 'Status', readonly=True, select=True, copy=False, default='new')
    alerts = fields.Text(
        compute='_compute_alerts_get', string="Alerts", default=_default_alerts_get)

    @api.multi
    def _compute_alerts_get(self):
        """
        get the alerts to display on the order form
        """
        for order in self:
            if order.state == 'new':
                order.alerts = self._default_alerts_get()

    @api.multi
    def name_get(self):
        return [(elmt.id, "%s %s" % (_('Lunch Order'), elmt.id)) for elmt in self]

    @api.multi
    def _update_order_state(self):
        """
        Update the state of lunch.order based on its orderlines
        """
        for order in self:
            isconfirmed = True
            for orderline in order.order_line_ids:
                if orderline.state == 'new':
                    isconfirmed = False
                if orderline.state == 'cancelled':
                    isconfirmed = False
                    order.state = 'partially'
            if isconfirmed:
                order.state = 'confirmed'


class lunch_order_line(models.Model):

    """
    lunch order line: one lunch order can have many order lines
    """
    _name = 'lunch.order.line'
    _description = 'lunch order line'

    @api.onchange('product_id')
    def onchange_price(self):
        self.price = self.product_id.price

    @api.multi
    def order(self):
        """
        The order_line is ordered to the supplier but isn't received yet
        """
        self.write({'state': 'ordered'})
        orders = self.env['lunch.order'].search(
            [('order_line_ids', 'in', self.ids)])
        return orders._update_order_state()

    @api.multi
    def confirm(self):
        """
        confirm one or more order line, update order status and create new cashmove
        """
        for order_line in self:
            if order_line.state != 'confirmed':
                values = {
                    'user_id': order_line.user_id.id,
                    'amount': -order_line.price,
                    'description': order_line.product_id.name,
                    'order_id': order_line.id,
                    'state': 'order',
                    'date': order_line.date,
                }
                self.env['lunch.cashmove'].create(values)
                order_line.state = 'confirmed'
        orders = self.env['lunch.order'].search(
            [('order_line_ids', 'in', self.ids)])
        return orders._update_order_state()

    @api.multi
    def cancel(self):
        """
        cancel one or more order.line, update order status and unlink existing cashmoves
        """
        self.write({'state': 'cancelled'})
        for order_line in self:
            order_line.cashmove.unlink()
        orders = self.env['lunch.order'].search(
            [('order_line_ids', 'in', self.ids)])
        return orders._update_order_state()

    name = fields.Char(string='name', related='product_id.name', readonly=True)
    order_id = fields.Many2one('lunch.order', 'Order', ondelete='cascade')
    product_id = fields.Many2one('lunch.product', 'Product', required=True)
    category_id = fields.Many2one(
        'lunch.product.category', string='Product Category', related='product_id.category_id', readonly=True, store=True)
    date = fields.Date(
        string='Date', related='order_id.date', readonly=True, store=True)
    supplier = fields.Many2one(
        'res.partner', string='Supplier', related='product_id.supplier', readonly=True, store=True)
    user_id = fields.Many2one(
        'res.users', string='User', related='order_id.user_id', readonly=True, store=True)
    note = fields.Text('Note')
    price = fields.Float("Price")
    state = fields.Selection([('new', 'New'),
                              ('confirmed', 'Received'),
                              ('ordered', 'Ordered'),
                              ('cancelled', 'Cancelled')],
                             'Status', readonly=True, select=True, default='new')
    cashmove = fields.One2many('lunch.cashmove', 'order_id', 'Cash Move')


class lunch_product(models.Model):

    """
    lunch product
    """
    _name = 'lunch.product'
    _description = 'lunch product'

    name = fields.Char('Product', required=True)
    category_id = fields.Many2one(
        'lunch.product.category', 'Category', required=True)
    description = fields.Text('Description')
    # TODO: use decimal precision of 'Account', move it from product to
    # decimal_precision
    price = fields.Float('Price', digits=(16, 2))
    supplier = fields.Many2one('res.partner', 'Supplier')


class lunch_product_category(models.Model):

    """
    lunch product category
    """
    _name = 'lunch.product.category'
    _description = 'lunch product category'

    # such as PIZZA, SANDWICH, PASTA, CHINESE, BURGER, ...
    name = fields.Char('Category', required=True)


class lunch_cashmove(models.Model):

    """
    lunch cashmove => order or payment
    """
    _name = 'lunch.cashmove'
    _description = 'lunch cashmove'

    user_id = fields.Many2one(
        'res.users', 'User Name', required=True, default=lambda self: self.env.uid)
    date = fields.Date(
        'Date', required=True, default=fields.Date.context_today)
    # depending on the kind of cashmove, the amount will be positive or
    # negative
    amount = fields.Float('Amount', required=True)
    # the description can be an order or a payment
    description = fields.Text('Description')
    order_id = fields.Many2one('lunch.order.line', 'Order', ondelete='cascade')
    state = fields.Selection(
        [('order', 'Order'), ('payment', 'Payment')], 'Is an order or a Payment', default='payment')

    @api.multi
    def name_get(self):
        return [(elmt.id, "%s %s" % (_('Lunch Cashmove'), elmt.id)) for elmt in self]


class lunch_alert(models.Model):

    """
    lunch alert
    """
    _name = 'lunch.alert'
    _description = 'Lunch Alert'

    message = fields.Text('Message', required=True)
    alert_type = fields.Selection([('specific', 'Specific Day'),
                                   ('week', 'Every Week'),
                                   ('days', 'Every Day')],
                                  string='Recurrency', required=True, select=True, default='specific')
    specific_day = fields.Date('Day', default=fields.Date.context_today)
    monday = fields.Boolean('Monday')
    tuesday = fields.Boolean('Tuesday')
    wednesday = fields.Boolean('Wednesday')
    thursday = fields.Boolean('Thursday')
    friday = fields.Boolean('Friday')
    saturday = fields.Boolean('Saturday')
    sunday = fields.Boolean('Sunday')
    start_hour = fields.Float(
        'Between', oldname='active_from', required=True, default=7)
    end_hour = fields.Float(
        'And', oldname='active_to', required=True, default=23)

    @api.multi
    def name_get(self):
        return [(elmt.id, "%s %s" % (_('Alert'), elmt.id)) for elmt in self]

    @api.model
    def get_alert_message(self):
        """
        This method check if the alert can be displayed today
        if alert type is specific : compare specific_day(date) with today's date
        if alert type is week : check today is set as alert (checkbox true) eg. self['monday']
        if alert type is day : True
        return : Message if can_display_alert is True else False
        """
        can_display_alert = {
            'specific': (self.specific_day == fields.Date.context_today(self)),
            'week': self[datetime.datetime.now().strftime('%A').lower()],
            'days': True
        }
        if can_display_alert[self.alert_type]:
            mynow = fields.Datetime.context_timestamp(
                self, datetime.datetime.now())
            hour_to = int(self.end_hour)
            min_to = int((self.end_hour - hour_to) * 60)
            to_alert = datetime.time(hour_to, min_to)
            hour_from = int(self.start_hour)
            min_from = int((self.start_hour - hour_from) * 60)
            from_alert = datetime.time(hour_from, min_from)
            if from_alert <= mynow.time() <= to_alert:
                return self.message
        return False
