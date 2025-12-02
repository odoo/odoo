# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.exceptions import UserError


class StockPickingToBatch(models.TransientModel):
    _name = 'stock.picking.to.batch'
    _description = 'Batch Transfer Lines'

    batch_id = fields.Many2one('stock.picking.batch', string='Batch Transfer', domain="[('is_wave', '=', False), ('state', 'in', ('draft', 'in_progress'))]")
    mode = fields.Selection([('existing', 'an existing batch transfer'), ('new', 'a new batch transfer')], default='new')
    user_id = fields.Many2one('res.users', string='Responsible')
    is_create_draft = fields.Boolean(string="Draft", help='When checked, create the batch in draft status')
    description = fields.Char('Description')

    def attach_pickings(self):
        self.ensure_one()
        pickings = self.env['stock.picking'].browse(self.env.context.get('active_ids'))
        if self.mode == 'new':
            company = pickings.company_id
            if len(company) > 1:
                raise UserError(_("The selected pickings should belong to an unique company."))
            batch = self.env['stock.picking.batch'].create({
                'user_id': self.user_id.id,
                'company_id': company.id,
                'picking_type_id': pickings[0].picking_type_id.id,
                'description': self.description,
            })
            notification_title = _('The following batch transfer has been created')
        else:
            batch = self.batch_id
            notification_title = _('The following batch transfer has been updated')

        pickings.write({'batch_id': batch.id})
        # you have to set some pickings to batch before confirm it.
        if self.mode == 'new' and not self.is_create_draft:
            batch.action_confirm()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': notification_title,
                'message': '%s',
                'links': [{
                    'label': batch.name,
                    'url': f'/odoo/action-stock_picking_batch.stock_picking_batch_action/{batch.id}',
                }],
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }
