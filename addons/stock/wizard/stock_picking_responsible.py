# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models
from odoo.exceptions import UserError


# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# TODO: REMOVE THIS FILE IN 13.1 !
# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
class StockPickingResponsible(models.TransientModel):
    _name = 'stock.picking.responsible'
    _description = 'Assign Responsible'

    user_id = fields.Many2one(
        'res.users', 'Responsible',
        domain=lambda self: [('groups_id', 'in', self.env.ref('stock.group_stock_user').id)],
        default=lambda self: self.env.user)

    def assign_responsible(self):
        self.ensure_one()
        pickings = self.env['stock.picking'].browse(self.env.context.get('active_ids'))
        restricted_companies = pickings.company_id - self.user_id.company_ids
        if restricted_companies:
            raise UserError(_('%s has a restricted access to %s') % (self.user_id.name, restricted_companies.mapped('name')))
        pickings.write({'user_id': self.user_id.id})
