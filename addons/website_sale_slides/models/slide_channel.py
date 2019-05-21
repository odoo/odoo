# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class Channel(models.Model):
    _inherit = 'slide.channel'

    enroll = fields.Selection(selection_add=[('payment', 'On payment')])
    product_id = fields.Many2one('product.product', 'Product', index=True)
    total_revenues = fields.Float(string="Revenues", compute="_compute_revenues", digits=(6,2))

    _sql_constraints = [
        ('product_id_check', "CHECK( enroll!='payment' OR product_id IS NOT NULL )", "Product is required for on payment channels.")
    ]

    def _filter_add_members(self, target_partners, **member_values):
        """ Overridden to add 'payment' channels to the filtered channels. People
        that can write on payment-based channels can add members. """
        result = super(Channel, self)._filter_add_members(target_partners, **member_values)
        on_payment = self.filtered(lambda channel: channel.enroll == 'payment')
        if on_payment:
            try:
                on_payment.check_access_rights('write')
                on_payment.check_access_rule('write')
            except:
                pass
            else:
                result |= on_payment
        return result

    @api.depends('product_id','enroll')
    def _compute_revenues(self):
        for channel in self:
            if(channel.enroll == 'payment'):
                sale_report = self.env['sale.report'].search([['product_id','=',channel.product_id.id]])
                for sale in sale_report:
                    channel.total_revenues += sale.price_total
