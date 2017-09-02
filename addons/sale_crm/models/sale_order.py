# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class SaleOrder(models.Model):
    _name = "sale.order"
    _inherit = ['sale.order', 'utm.mixin']

    tag_ids = fields.Many2many('crm.lead.tag', 'sale_order_tag_rel', 'order_id', 'tag_id', string='Tags')
    opportunity_id = fields.Many2one('crm.lead', string='Opportunity', domain="[('type', '=', 'opportunity')]")

    @api.model
    def create(self, vals):
        order = super(SaleOrder, self).create(vals)
        if vals.get('opportunity_id'):
            message = _("This order has been created from: <a href=# data-oe-model=crm.lead data-oe-id=%d>%s</a>") % (order.opportunity_id.id, order.opportunity_id.name)
            order.message_post(body=message)
        return order
