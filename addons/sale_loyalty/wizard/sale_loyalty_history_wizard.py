# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class SaleLoyaltyHistoryWizard(models.TransientModel):
    _name = 'sale.loyalty.history.wizard'
    _description = 'History Coupons'

    coupon_id = fields.Many2one(
        comodel_name='loyalty.card',
        required=True,
        # compute='_useless_compute',
        default=lambda self: self.env.context.get('active_id') or
            self.env.context.get('default_coupon_id', False)
    )
    points_old = fields.Float(
        # compute='_useless_compute',
        related='coupon_id.points',
        string="Old balance",
        depends=['coupon_id']
    )
    points_new = fields.Float(default=200.0, string="New balance")
    description = fields.Char(default="Refund of ...", string="Descriptions")

    # def _useless_compute(self):
    #     for record in self:
    #         record.coupon_id = record.env.context.get('active_id', False) or record.env.context.get('default_coupon_id', False)
    # @api.depends('coupon_id')
    # def _useless_compute(self):
    #     for record in self:
    #         record.points_old = record.coupon_id.points

    def history_coupons(self):
        if self.points_old == self.points_new:
            raise ValidationError(_("Invalid balanced."))
        self.coupon_id.history_ids += self.env['sale.loyalty.history'].create({
                'coupon_id': self.coupon_id.id,
                'description': self.description,
                'used': -(self.points_old - self.points_new)
                    if self.points_old > self.points_new else 0,
                'issued': self.points_new - self.points_old
                    if self.points_old < self.points_new else 0,
                'new_balance': self.points_new,
            })
        self.coupon_id.points = self.points_new
        return True
