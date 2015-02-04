# -*- coding: utf-8 -*-
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from openerp import tools, models, fields, api, _


class sale_order(models.Model):
    _inherit = 'sale.order'

    @api.multi
    def check_coupon(self):
        self.has_coupon = any([(not l.is_coupon and l.coupon_ids)
                              for order in self for l in order.order_line])

    has_coupon = fields.Boolean(compute="check_coupon")


class sale_order_line(models.Model):
    _inherit = 'sale.order.line'

    sales_coupon_type_id = fields.Many2one(
        'sales.coupon.type', string='Coupon Type')
    coupon_ids = fields.Many2many('sales.coupon', 'sale_order_coupon_rel',
                                  'order_id', 'coupon_id', string='Sales Coupon', readonly=True, store=True)
    is_coupon = fields.Boolean()

    def _prepare_coupon_so_line(self, coupon):
        return {
            'order_id': self.order_id.id,
            'name': _('Coupon : %s , Product: %s') % (coupon.code, coupon.product_id.name),
            'price_unit': - coupon.product_id.list_price,
            'coupon_ids': [(4, coupon.id)],
            'is_coupon': True,
        }

    def _prepare_product_coupon_so_line(self, coupon):
        return {
            'order_id': self.order_id.id,
            'product_id': coupon.product_id.id,
            'name': coupon.product_id.name,
            'product_uom_qty': 1,
            'price_unit': coupon.product_id.list_price,
            'coupon_ids': [(4, coupon.id)],
            'is_coupon': True,
        }

    @api.multi
    def apply_coupon(self, promocode):
        coupon = self.env['sales.coupon'].search([('code', '=', promocode)])
        if coupon:
            if coupon.line_id and coupon.line_id.state != 'done':
                return {'error': _('you can not use %s. Code is not activated or your previous order not completed.') % (promocode)}
            check_expiration = coupon.check_expiration()[0]
            if check_expiration:
                return check_expiration
            if coupon.id in [coupon_id.id for line in self for coupon_id in line.coupon_ids]:
                return {'error': _('Coupon %s already applied on %s.') % (promocode, coupon.product_id.name)}
            if any([line_ids.product_id.id == coupon.product_id.id for line_ids in self]):
                for line in self.search([('product_id', '=', coupon.product_id.id)]):
                    if len([code.id for code in line.coupon_ids]) > 0:
                        line.product_uom_qty = line.product_uom_qty + 1
                    # line.write({'coupon_id': [(4, coupon.id)], 'is_coupon': True})
                    line.coupon_ids = [(4, coupon.id)]
                    line.is_coupon = True
                    line.create(line._prepare_coupon_so_line(coupon))
                    coupon.post_apply()
                    return {'update_price': 'update_cart_price'}
            else:
                self.create(self._prepare_product_coupon_so_line(coupon))
                self.create(self._prepare_coupon_so_line(coupon))
                coupon.post_apply()
                return {'update_price': 'update_cart_price'}

    @api.multi
    def product_id_change(self, pricelist, product, qty=0,
                          uom=False, qty_uos=0, uos=False, name='', partner_id=False,
                          lang=False, update_tax=True, date_order=False, packaging=False, fiscal_position=False, flag=False):
        res = super(sale_order_line, self).product_id_change(
            pricelist, product)
        products = self.env['product.product'].browse(product)
        res['value'].update(
            {'sales_coupon_type_id': products.product_tmpl_id.coupon_type.id or products.coupon_type.id})
        return res

    def _prepare_coupon(self):
        order_date = datetime.strptime(
            self.order_id.date_order, tools.DEFAULT_SERVER_DATETIME_FORMAT).date()
        return{
            'partner_id': self.order_id.partner_id.id,
            'coupon_type': self.sales_coupon_type_id.id,
            'product_id': self.product_id.id,
            'expiration_date': self.env['sales.coupon.type'].browse([self.sales_coupon_type_id.id]).get_expiration_date(order_date),
            'expiration_use': self.sales_coupon_type_id.expiration_use,
            'line_id': self.id,
        }

    @api.multi
    def _generate_coupon(self):
        sales_coupon_obj = self.env['sales.coupon']
        for line in self:
            qty = int(line.product_uom_qty)
            while qty > 0:
                if line.sales_coupon_type_id.id and not line.is_coupon and line.sales_coupon_type_id.is_active:
                    coupon = sales_coupon_obj.create(line._prepare_coupon())
                    line.coupon_ids = [(4, coupon.id)]
                qty = qty - 1
        return True

    @api.multi
    def unlink(self):
        line = self.coupon_ids and self.search(
            [('order_id', '=', self.order_id.id), ('coupon_ids', '=', self.coupon_ids.id), ('id', 'not in', self.ids)])
        if line:
            super(sale_order_line, line).unlink()
        return super(sale_order_line, self).unlink()

    @api.multi
    def button_confirm(self):
        res = super(sale_order_line, self).button_confirm()
        self._generate_coupon()
        return res
