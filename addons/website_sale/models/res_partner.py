# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.http import request


class ResPartner(models.Model):
    _inherit = 'res.partner'

    last_website_so_id = fields.Many2one('sale.order', compute='_compute_last_website_so_id', string='Last Online Sales Order')

    @api.multi
    def _compute_last_website_so_id(self):
        SaleOrder = self.env['sale.order']
        for partner in self:
            is_public = any([u._is_public()
                             for u in partner.with_context(active_test=False).user_ids])
            if request and hasattr(request, 'website') and not is_public:
                partner.last_website_so_id = SaleOrder.search([
                    ('partner_id', '=', partner.id),
                    ('website_id', '=', request.website.id),
                    ('state', '=', 'draft'),
                ], order='write_date desc', limit=1)
            else:
                partner.last_website_so_id = SaleOrder  # Not in a website context or public User
