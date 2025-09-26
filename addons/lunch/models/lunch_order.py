# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

from odoo.exceptions import ValidationError, UserError
from odoo.fields import Domain


class LunchOrder(models.Model):
    _name = 'lunch.order'
    _description = 'Lunch Order'
    _order = 'id desc'
    _display_name = 'product_id'

    name = fields.Char(related='product_id.name', string="Product Name", readonly=True)
    topping_ids_1 = fields.Many2many('lunch.topping', 'lunch_order_topping', 'order_id', 'topping_id', string='Extras 1', domain=[('topping_category', '=', 1)])
    topping_ids_2 = fields.Many2many('lunch.topping', 'lunch_order_topping', 'order_id', 'topping_id', string='Extras 2', domain=[('topping_category', '=', 2)])
    topping_ids_3 = fields.Many2many('lunch.topping', 'lunch_order_topping', 'order_id', 'topping_id', string='Extras 3', domain=[('topping_category', '=', 3)])
    product_id = fields.Many2one('lunch.product', string="Product", required=True)
    category_id = fields.Many2one(
        string='Product Category', related='product_id.category_id', store=True)
    date = fields.Date('Order Date', required=True, readonly=False,
                       default=fields.Date.context_today)
    supplier_id = fields.Many2one(
        string='Vendor', related='product_id.supplier_id', store=True, index=True)
    available_today = fields.Boolean(related='supplier_id.available_today')

    available_on_date = fields.Boolean(compute='_compute_available_on_date')
    order_deadline_passed = fields.Boolean(compute='_compute_order_deadline_passed')
    user_id = fields.Many2one('res.users', 'User', default=lambda self: self.env.uid)
    lunch_location_id = fields.Many2one('lunch.location', default=lambda self: self.env.user.last_lunch_location_id)
    note = fields.Text('Notes')
    price = fields.Monetary('Total Price', compute='_compute_total_price', readonly=True, store=True)
    active = fields.Boolean('Active', default=True)
    state = fields.Selection([('new', 'To Order'),
                              ('ordered', 'Ordered'),       # "Internally" ordered
                              ('sent', 'Sent'),             # Order sent to the supplier
                              ('confirmed', 'Received'),    # Order received
                              ('cancelled', 'Cancelled')],
                             'Status', readonly=True, index=True, default='new')
    notified = fields.Boolean(default=False)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company.id)
    currency_id = fields.Many2one(related='company_id.currency_id', store=True)
    quantity = fields.Float('Quantity', required=True, default=1)

    display_toppings = fields.Text('Extras', compute='_compute_display_toppings', store=True)

    product_description = fields.Html('Description', related='product_id.description')
    topping_label_1 = fields.Char(related='product_id.supplier_id.topping_label_1')
    topping_label_2 = fields.Char(related='product_id.supplier_id.topping_label_2')
    topping_label_3 = fields.Char(related='product_id.supplier_id.topping_label_3')
    topping_quantity_1 = fields.Selection(related='product_id.supplier_id.topping_quantity_1')
    topping_quantity_2 = fields.Selection(related='product_id.supplier_id.topping_quantity_2')
    topping_quantity_3 = fields.Selection(related='product_id.supplier_id.topping_quantity_3')
    image_1920 = fields.Image(compute='_compute_product_images')
    image_128 = fields.Image(compute='_compute_product_images')

    available_toppings_1 = fields.Boolean(help='Are extras available for this product', compute='_compute_available_toppings')
    available_toppings_2 = fields.Boolean(help='Are extras available for this product', compute='_compute_available_toppings')
    available_toppings_3 = fields.Boolean(help='Are extras available for this product', compute='_compute_available_toppings')
    display_reorder_button = fields.Boolean(compute='_compute_display_reorder_button')
    display_add_button = fields.Boolean(compute='_compute_display_add_button')

    _user_product_date = models.Index("(user_id, product_id, date)")

    @api.depends('product_id')
    def _compute_product_images(self):
        for line in self:
            line.image_1920 = line.product_id.image_1920 or line.category_id.image_1920
            line.image_128 = line.product_id.image_128 or line.category_id.image_128

    @api.depends('category_id')
    def _compute_available_toppings(self):
        for order in self:
            order.available_toppings_1 = bool(order.env['lunch.topping'].search_count([('supplier_id', '=', order.supplier_id.id), ('topping_category', '=', 1)]))
            order.available_toppings_2 = bool(order.env['lunch.topping'].search_count([('supplier_id', '=', order.supplier_id.id), ('topping_category', '=', 2)]))
            order.available_toppings_3 = bool(order.env['lunch.topping'].search_count([('supplier_id', '=', order.supplier_id.id), ('topping_category', '=', 3)]))

    @api.depends('name')
    def _compute_display_add_button(self):
        new_orders = dict(self.env["lunch.order"]._read_group([
            ("date", "in", self.mapped("date")),
            ("user_id", "in", self.user_id.ids),
            ("state", "=", "new"),
        ], ['user_id'], ['id:recordset']))
        for order in self:
            user_new_orders = new_orders.get(order.user_id)
            price = 0
            if user_new_orders:
                user_new_orders = user_new_orders.filtered(lambda lunch_order: lunch_order.date == order.date)
                price = sum(order.price for order in user_new_orders)
            wallet_amount = self.env['lunch.cashmove'].get_wallet_balance(order.user_id) - price
            order.display_add_button = wallet_amount >= order.price

    @api.depends_context('show_reorder_button')
    @api.depends('state')
    def _compute_display_reorder_button(self):
        show_button = self.env.context.get('show_reorder_button')
        for order in self:
            order.display_reorder_button = show_button and order.state == 'confirmed' and order.supplier_id.available_today

    @api.depends('date', 'supplier_id')
    def _compute_available_on_date(self):
        for order in self:
            order.available_on_date = order.supplier_id._available_on_date(order.date)

    @api.depends('supplier_id', 'date')
    def _compute_order_deadline_passed(self):
        today = fields.Date.context_today(self)
        for order in self:
            if order.date < today:
                order.order_deadline_passed = True
            elif order.date == today:
                order.order_deadline_passed = order.supplier_id.order_deadline_passed
            else:
                order.order_deadline_passed = False

    def _get_topping_ids(self, field, values):
        return list(self._fields[field].convert_to_cache(values, self))

    def _extract_toppings(self, values):
        """
            If called in api.multi then it will pop topping_ids_1,2,3 from values
        """
        topping_ids = []

        for i in range(1, 4):
            topping_field = f'topping_ids_{i}'
            topping_values = values.get(topping_field, False)

            if self.ids:
                # TODO This is not taking into account all the toppings for each individual order, this is usually not a problem
                # since in the interface you usually don't update more than one order at a time but this is a bug nonetheless
                topping_ids += self._get_topping_ids(topping_field, values.pop(topping_field)) \
                    if topping_values else self[:1][topping_field].ids
            else:
                topping_ids += self._get_topping_ids(topping_field, topping_values) if topping_values else []

        return topping_ids

    @api.constrains('topping_ids_1', 'topping_ids_2', 'topping_ids_3')
    def _check_topping_quantity(self):
        errors = {
            '1_more': _('You should order at least one %s'),
            '1': _('You have to order one and only one %s'),
        }
        for line in self:
            for index in range(1, 4):
                availability = line['available_toppings_%s' % index]
                quantity = line['topping_quantity_%s' % index]
                toppings = line['topping_ids_%s' % index].filtered(lambda x: x.topping_category == index)
                label = line['topping_label_%s' % index]

                if availability and quantity != '0_more':
                    check = bool(len(toppings) == 1 if quantity == '1' else toppings)
                    if not check:
                        raise ValidationError(errors[quantity] % label)

    @api.model_create_multi
    def create(self, vals_list):
        orders = self.env['lunch.order']
        for vals in vals_list:
            lines = self._find_matching_lines({
                **vals,
                'toppings': self._extract_toppings(vals),
                'state': 'new',
            })
            if lines:
                # YTI FIXME This will update multiple lines in the case there are multiple
                # matching lines which should not happen through the interface
                lines.update_quantity(1)
                orders |= lines[:1]
            else:
                orders |= super().create(vals)
        return orders

    def write(self, vals):
        values = vals
        change_topping = 'topping_ids_1' in values or 'topping_ids_2' in values or 'topping_ids_3' in values
        merge_needed = 'note' in values or change_topping or 'state' in values
        default_location_id = self.env.user.last_lunch_location_id and self.env.user.last_lunch_location_id.id or False

        if merge_needed:
            lines_to_deactivate = self.env['lunch.order']
            for line in self:
                # Only write on topping_ids_1 because they all share the same table
                # and we don't want to remove all the records
                # _extract_toppings will pop topping_ids_1, topping_ids_2 and topping_ids_3 from values
                # This also forces us to invalidate the cache for topping_ids_2 and topping_ids_3 that
                # could have changed through topping_ids_1 without the cache knowing about it
                toppings = self._extract_toppings(values)
                if change_topping:
                    self.invalidate_model(['topping_ids_2', 'topping_ids_3'])
                    values['topping_ids_1'] = [(6, 0, toppings)]
                matching_lines = self._find_matching_lines({
                    'user_id': values.get('user_id', line.user_id.id),
                    'product_id': values.get('product_id', line.product_id.id),
                    'note': values.get('note', line.note or False),
                    'toppings': toppings,
                    'lunch_location_id': values.get('lunch_location_id', default_location_id),
                    'state': values.get('state'),
                })
                if matching_lines:
                    lines_to_deactivate |= line
                    matching_lines.update_quantity(line.quantity)
            lines_to_deactivate.write({'active': False})
            return super(LunchOrder, self - lines_to_deactivate).write(values)
        return super().write(values)

    @api.model
    def _find_matching_lines(self, values):
        default_location_id = self.env.user.last_lunch_location_id and self.env.user.last_lunch_location_id.id or False
        domain = [
            ('user_id', '=', values.get('user_id', self.default_get(['user_id'])['user_id'])),
            ('product_id', '=', values.get('product_id', False)),
            ('date', '=', values.get('date', fields.Date.today())),
            ('note', '=', values.get('note', False)),
            ('lunch_location_id', '=', values.get('lunch_location_id', default_location_id)),
        ]
        if values.get('state'):
            domain = Domain.AND([domain, [('state', '=', values['state'])]])
        toppings = values.get('toppings', [])
        return self.search(domain).filtered(lambda line: (line.topping_ids_1 | line.topping_ids_2 | line.topping_ids_3).ids == toppings)

    @api.depends('topping_ids_1', 'topping_ids_2', 'topping_ids_3', 'product_id', 'quantity')
    def _compute_total_price(self):
        for line in self:
            line.price = line.quantity * (line.product_id.price + sum((line.topping_ids_1 | line.topping_ids_2 | line.topping_ids_3).mapped('price')))

    @api.depends('topping_ids_1', 'topping_ids_2', 'topping_ids_3')
    def _compute_display_toppings(self):
        for line in self:
            toppings = line.topping_ids_1 | line.topping_ids_2 | line.topping_ids_3
            line.display_toppings = ' + '.join(toppings.mapped('name'))

    def update_quantity(self, increment):
        for line in self.filtered(lambda line: line.state not in ['sent', 'confirmed']):
            if line.quantity <= -increment:
                # TODO: maybe unlink the order?
                line.active = False
            else:
                line.quantity += increment
        self._check_wallet()

    def add_to_cart(self):
        """
            This method currently does nothing, we currently need it in order to
            be able to reuse this model in place of a wizard
        """
        # YTI FIXME: Find a way to drop this.
        return True

    def _check_wallet(self):
        self.env.flush_all()
        for line in self:
            if self.env['lunch.cashmove'].get_wallet_balance(line.user_id) < 0:
                raise ValidationError(_('Oh no! You don’t have enough money in your wallet to order your selected lunch! Contact your lunch manager to add some money to your wallet.'))

    def action_order(self):
        for order in self:
            if not order.available_on_date:
                raise UserError(_('The vendor related to this order is not available at the selected date.'))
        if self.filtered(lambda line: not line.product_id.active):
            raise ValidationError(_('Product is no longer available.'))
        self.write({
            'state': 'ordered',
        })
        self._check_wallet()

    def action_reorder(self):
        self.ensure_one()
        if not self.supplier_id.available_today:
            raise UserError(_('The vendor related to this order is not available today.'))
        self.copy({
            'date': fields.Date.context_today(self),
            'state': 'ordered',
        })
        action = self.env['ir.actions.act_window']._for_xml_id('lunch.lunch_order_action')
        return action

    def action_confirm(self):
        self.write({'state': 'confirmed'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_reset(self):
        self.write({'state': 'ordered'})

    def action_send(self):
        self.state = 'sent'

    def action_notify(self):
        self -= self.filtered('notified')
        if not self:
            return
        notified_users = set()
        # (company, lang): (subject, body)
        translate_cache = dict()
        for order in self:
            user = order.user_id
            if user in notified_users:
                continue
            _key = (order.company_id, user.lang)
            if _key not in translate_cache:
                context = {'lang': user.lang}
                translate_cache[_key] = (_('Lunch notification'), order.company_id.with_context(lang=user.lang).lunch_notify_message)
                del context
            subject, body = translate_cache[_key]
            user.partner_id.message_notify(
                subject=subject,
                body=body,
                partner_ids=user.partner_id.ids,
                email_layout_xmlid='mail.mail_notification_light',
            )
            notified_users.add(user)
        self.write({'notified': True})
