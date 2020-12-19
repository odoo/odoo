# -*- coding: utf-8 -*-

from odoo import models, fields, api


class addtest(models.Model):
    _inherit = 'stock.move'

    # 发生变化时执行函数
    @api.onchange('product_id')
    def onchange_product_num(self):
        product = self.product_id.with_context(lang=self.partner_id.lang or self.env.user.lang)
        print(product.mapped('product_tmpl_id').mapped('list_price'))
        price_product = product.mapped('product_tmpl_id').mapped('list_price')
        if price_product:
            self.price = product.mapped('product_tmpl_id').mapped('list_price')[0]
        else:
            self.price = 0

    # def _compute_default_value(self):
    #     if self.sale_line_id:
    #         return self.sale_line_id.product_uom_qty
    #     else:
    #         return 1

    def _auot_pie(self):
        for aa in self:
            pieces_pairs = aa.sale_line_id.mapped('product_uom_qty')
            if pieces_pairs:
                aa.pieces_pairs = int(pieces_pairs[0])

            else:
                aa.pieces_pairs = 1

    price = fields.Float('价格', default=0)
    pieces = fields.Integer('件数',related='sale_line_id.pieces', readyonly=True)
    pieces_pairs = fields.Integer('件双数', related='sale_line_id.pieces_pairs', readyonly=True)


    @api.onchange('pieces')
    def onchange_done_num(self):
        for res in self:
            sum2 = res.pieces * res.pieces_pairs
            if sum2 <= res.product_uom_qty:
                res.product_uom_qty = sum2
            else:
                res.pieces = res.product_uom_qty / res.pieces_pairs
                warning = {
                    'title': "操作出错!",
                    'message': "数量总和不能超过完成数量",
                }
                return {'warning': warning}

        # for move in self:
        #     move.product_uom_qty = move.pieces * move.pieces_pairs


class addtest22(models.Model):
    _inherit = 'stock.move.line'

    def _auot_pie(self):
        for aa in self:
            pieces_pairs = aa.move_id.sale_line_id.mapped('product_uom_qty')
            if pieces_pairs:
                aa.pieces_pairs = int(pieces_pairs[0])

            else:
                aa.pieces_pairs = 1

    # 价格
    @api.onchange('product_id')
    def onchange_product_num(self):
        product = self.product_id
        print(product.mapped('product_tmpl_id').mapped('list_price'))
        price_product = product.mapped('product_tmpl_id').mapped('list_price')
        if price_product:
            self.price = product.mapped('product_tmpl_id').mapped('list_price')[0]
        else:
            self.price = 0

    price = fields.Float('价格', default=0)
    pieces = fields.Integer('件数', default=0)
    # pieces_pairs = fields.Integer('件双数', default=1, compute=_auot_pie)
    pieces_pairs = fields.Integer('件双数', related='move_id.sale_line_id.pieces_pairs', readyonly=True)


    @api.onchange('pieces')
    def onchange_done_num(self):
        for res in self:
            sum2 = res.pieces * res.pieces_pairs
            print(res.product_uom_qty)
            if sum2 <= 1000:
                res.qty_done = int(sum2)
            else:
                res.pieces = int(res.product_uom_qty / res.pieces_pairs)
                warning = {
                    'title': "操作出错!",
                    'message': "数量总和错误",
                }
                return {'warning': warning}

# product_id = fields.Many2one(
#     'product.product', 'Product',
#     check_company=True,
#     domain="[('type', 'in', ['product', 'consu']), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
#     index=True, required=True,
#     states={'done': [('readonly', True)]})

# def _price22(self):
#     stock_move = self.env['stock.move'].search([])
#     res = stock_move.filtered(lambda r: r.id == self.env.uid).product_id.product_tmpl_id.id
#     print(res)
#     product_template = self.env['product.template'].search([])
#     price = product_template.filtered(lambda r: r.id == res).list_price
#     print(price)
#     return price
