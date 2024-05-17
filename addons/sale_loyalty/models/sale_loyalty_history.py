# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class SaleLoyaltyHistory(models.Model):
    _name = 'sale.loyalty.history'
    _description = 'Sale Loyalty History'

    coupon_id = fields.Many2one(
        comodel_name='loyalty.card',
    )
    company_id = fields.Many2one(related='coupon_id.company_id')
    sale_order_id = fields.Many2one(
        comodel_name='sale.order',
        domain=[('order_line.coupon_id', '=', coupon_id)]
    )
    sale_order_name = fields.Char(related='sale_order_id.name')
    description = fields.Char(default="\(*-*)/")
    date = fields.Datetime(related='sale_order_id.date_order')
    issued = fields.Float(default=0)
    issued_display = fields.Char(compute='_compute_issued_display')
    used = fields.Float(default=0)
    used_display = fields.Char(compute='_compute_used_display')
    new_balance = fields.Float(default=lambda self: self.coupon_id.points, store=True)


    def _get_top_up_options(self):
        values = [25, 50, 100, 200]
        return [
            (str(index), self.coupon_id._format_points(value))
            for index, value in enumerate([25, 50, 100, 200])
        ]

    top_up_options = fields.Selection(
        selection=_get_top_up_options,
        default='0'
    )

    @api.depends('issued')
    def _compute_issued_display(self):
        for transaction in self:
            transaction.issued_display = transaction.coupon_id._format_points(transaction.issued)

    @api.depends('used')
    def _compute_used_display(self):
        for transaction in self:
            transaction.used_display = transaction.coupon_id._format_points(transaction.used)

    # TODO ASK: ADD a line in the history for creation
    # date = fields.Datetime(compute='_compute_date', store=True)
    # @api.depends('sale_order_id')
    # def _compute_date(self):
    #     for transaction in self:
    #         if transaction.sale_order_id:
    #             transaction.date = transaction.sale_order_id.date_order
    #         else:
    #             transaction.date = fields.Datetime.now()
