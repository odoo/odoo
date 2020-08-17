# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class Channel(models.Model):
    _inherit = 'slide.channel'

    enroll = fields.Selection(selection_add=[
        ('payment', 'On payment')
    ], ondelete={'payment': lambda recs: recs.write({'enroll': 'invite'})})
    product_id = fields.Many2one('product.product', 'Product', index=True)
    product_sale_revenues = fields.Monetary(
        string='Total revenues', compute='_compute_product_sale_revenues',
        groups="sales_team.group_sale_salesman")
    currency_id = fields.Many2one(related='product_id.currency_id')

    _sql_constraints = [
        ('product_id_check', "CHECK( enroll!='payment' OR product_id IS NOT NULL )", "Product is required for on payment channels.")
    ]

    @api.depends('product_id')
    def _compute_product_sale_revenues(self):
        domain = [
            ('state', 'in', self.env['sale.report']._get_done_states()),
            ('product_id', 'in', self.product_id.ids),
        ]
        rg_data = dict(
            (item['product_id'][0], item['price_total'])
            for item in self.env['sale.report'].read_group(domain, ['product_id', 'price_total'], ['product_id'])
        )
        for channel in self:
            channel.product_sale_revenues = rg_data.get(channel.product_id.id, 0)

    @api.model
    def create(self, vals):
        channel = super(Channel, self).create(vals)
        if channel.enroll == 'payment':
            channel._synchronize_product_publish()
        return channel

    def write(self, vals):
        res = super(Channel, self).write(vals)
        if 'is_published' in vals:
            self.filtered(lambda channel: channel.enroll == 'payment')._synchronize_product_publish()
        return res

    def _synchronize_product_publish(self):
        self.filtered(lambda channel: channel.is_published and not channel.product_id.is_published).sudo().product_id.write({'is_published': True})
        self.filtered(lambda channel: not channel.is_published and channel.product_id.is_published).sudo().product_id.write({'is_published': False})

    def action_view_sales(self):
        action = self.env["ir.actions.actions"]._for_xml_id("website_sale_slides.sale_report_action_slides")
        action['domain'] = [('product_id', 'in', self.product_id.ids)]
        return action

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
