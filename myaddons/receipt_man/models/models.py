# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class Product(models.Model):
    """
    产品类
    """
    _name = "receipt.product"
    _description = u"产品类"

    code = fields.Char(string=u"产品代码", required = True, index = True)
    name = fields.Char(string=u"品名")
    speci = fields.Char(string=u"规格")
    uom = fields.Char(string=u"单位")
    price = fields.Float(string=u"单价")
    image = fields.Binary(string=u"产品图片", attachment=True)

    _sql_constraints = [
        ('receipt_product_code_uniq', 'unique (code)', u'该货号已存在，不能重复添加!'),
    ]

class Pertner(models.Model):
    _name = "receipt.partner"
    _description = u"合作伙伴"

    name = fields.Char(string=u"合作伙伴名称", required=True, index=True)
    address = fields.Char(string=u"地址")
    delivery_address = fields.Char(string=u"收货地址")
    phone = fields.Char(string=u"电话")
    website = fields.Char(string=u"公司网站")
    logo = fields.Binary(string=u"公司LOGO", attachment=True)

    _sql_constraints = [
        ('receipt_vendor_name_uniq', 'unique (name)', u'该合作伙伴已存在，不能重复添加!'),
    ]

class GodownEntry(models.Model):
    _name = "receipt.godown.entry"
    _description = u"入库单"

    name = fields.Char(string=u'入库单号', required=True, readonly=True, copy=False, index=True, default=lambda self: _('New'))
    purchase_order = fields.Char(string=u'采购单号')
    partner = fields.Many2one("receipt.partner", string=u'供货商')
    inbound_time = fields.Datetime(string=u'入库时间', required=True)
    closed = fields.Boolean(string=u'是否已结算')
    lines = fields.One2many("receipt.godown.entry.line", "godown_entry", string=u"入库明细")

    _sql_constraints = [
        ('receipt_godown_entry_name_uniq', 'unique (name)', u'该入库单已存在，不能重复添加!'),
    ]

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('cf.receipt.godown.entry') or _('New')
        result = super(GodownEntry, self).create(vals)
        return result

class GodownEntryLine(models.Model):
    _name = "receipt.godown.entry.line"
    _description = u"入库单明细"

    godown_entry = fields.Many2one("receipt.godown.entry", string=u"入库单")
    product = fields.Many2one("receipt.product", string=u"产品", required=True)
    qty_purchase = fields.Float(string=u"订单数量")
    qty_stock = fields.Float(string=u"入库数量", required=True)
    uom = fields.Char(string=u"单位")
    price_unit = fields.Float(string=u"单价")
    price = fields.Float(string=u"金额")

    @api.onchange('product')
    def onchange_product(self):
        if self.price_unit <= 0 and self.product.price > 0 :
            self.price_unit = self.product.price
        if not self.uom and self.product.uom:
            self.uom = self.product.uom

    @api.onchange('qty_stock')
    def onchange_qty_stock(self):
        if self.price <= 0 and self.price_unit > 0:
            self.price = self.price_unit * self.qty_stock

class DeliveryOrder(models.Model):
    _name = "receipt.delivery.order"
    _description = u"出货单"

    name = fields.Char(string=u'出货单号', required=True, readonly=True, copy=False, index=True, default=lambda self: _('New'))
    sale_order = fields.Char(string=u'销售单号')
    partner = fields.Many2one("receipt.partner", string=u'客户')
    outbound_time = fields.Datetime(string=u'出货时间', required=True)
    closed = fields.Boolean(string=u'是否已出库')
    lines = fields.One2many("receipt.delivery.order.line", "delivery_order", string=u"出货明细")

    _sql_constraints = [
        ('receipt_delivery_order_name_uniq', 'unique (name)', u'该出货单已存在，不能重复添加!'),
    ]

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('cf.receipt.delivery.order') or _('New')
        result = super(DeliveryOrder, self).create(vals)
        return result

class DeliveryOrderLine(models.Model):
    _name = "receipt.delivery.order.line"
    _description = u"出货单明细"

    delivery_order = fields.Many2one("receipt.delivery.order", string=u"出货单")
    product = fields.Many2one("receipt.product", string=u"产品", required=True)
    qty_order = fields.Float(string=u"订单数量")
    qty_outbound = fields.Float(string=u"出库数量", required=True)
    uom = fields.Char(string=u"单位")
    price_unit = fields.Float(string=u"单价")
    price = fields.Float(string=u"金额")

    @api.onchange('product')
    def onchange_product(self):
        if self.price_unit <= 0 and self.product.price > 0:
            self.price_unit = self.product.price
        if not self.uom and self.product.uom:
            self.uom = self.product.uom

    @api.onchange('qty_outbound')
    def onchange_qty_outbound(self):
        if self.price <= 0 and self.price_unit > 0:
            self.price = self.price_unit * self.qty_outbound

