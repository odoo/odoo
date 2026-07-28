# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import AccessError


class Channel(models.Model):
    _inherit = 'slide.channel'

    def _get_default_product_id(self):
        product_courses = self.env['product.product'].search(
            [('detailed_type', '=', 'course')], limit=2)
        return product_courses.id if len(product_courses) == 1 else False

    enroll = fields.Selection(selection_add=[
        ('payment', 'On payment')
    ], ondelete={'payment': lambda recs: recs.write({'enroll': 'invite'})})
    product_id = fields.Many2one('product.product', 'Product', domain=[('detailed_type', '=', 'course')],
                                 default=_get_default_product_id)
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
        rg_data = {
            product.id: price_total
            for product, price_total in self.env['sale.report']._read_group(domain, ['product_id'], ['price_total:sum'])
        }
        for channel in self:
            channel.product_sale_revenues = rg_data.get(channel.product_id.id, 0)

    @api.model_create_multi
    def create(self, vals_list):
        channels = super(Channel, self).create(vals_list)
        channels.filtered(lambda channel: channel.enroll == 'payment')._synchronize_product_publish()
        return channels

    def write(self, vals):
        res = super(Channel, self).write(vals)
        if 'is_published' in vals:
            self.filtered(lambda channel: channel.enroll == 'payment')._synchronize_product_publish()
        return res

    def _synchronize_product_publish(self):
        """
        Ensure that when publishing a course that its linked product is also published
        If all courses linked to a product are unpublished, we also unpublished the product
        """
        if not self:
            return
        self.filtered(lambda channel: channel.is_published and not channel.product_id.is_published).sudo().product_id.write({'is_published': True})

        unpublished_channel_products = self.filtered(lambda channel: not channel.is_published).product_id
        group_data = self._read_group(
            [('is_published', '=', True), ('product_id', 'in', unpublished_channel_products.ids)],
            ['product_id'],
        )
        used_product_ids = {product.id for [product] in group_data}
        product_to_unpublish = unpublished_channel_products.filtered(lambda product: product.id not in used_product_ids)
        if product_to_unpublish:
            product_to_unpublish.sudo().write({'is_published': False})

    def action_view_sales(self):
        action = self.env["ir.actions.actions"]._for_xml_id("website_sale_slides.sale_report_action_slides")
        action['domain'] = [('product_id', 'in', self.product_id.ids)]
        return action

    def _filter_add_members(self, target_partners, raise_on_access=False):
        """ Overridden to add 'payment' channels to the filtered channels. People
        that can write on payment-based channels can add members. """
        result = super(Channel, self)._filter_add_members(target_partners, raise_on_access=raise_on_access)
        on_payment = self.filtered(lambda channel: channel.enroll == 'payment')
        if on_payment:
            try:
                on_payment.check_access_rights('write')
                on_payment.check_access_rule('write')
            except AccessError:
                if raise_on_access:
                    raise AccessError(_('You are not allowed to add members to this course. Please contact the course responsible or an administrator.'))
            else:
                result |= on_payment
        return result
