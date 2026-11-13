# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    l10n_es_deca_picking_count = fields.Integer(compute='_compute_l10n_es_deca_picking_count')

    def _compute_l10n_es_deca_picking_count(self):
        for attachment in self:
            attachment.l10n_es_deca_picking_count = self.env['stock.picking'].search_count([('l10n_es_deca_attachment_ids', 'in', attachment.ids)])

    def action_l10n_es_open_deca_pickings(self):
        self.ensure_one()
        deca_pickings = self.env['stock.picking'].search([('l10n_es_deca_attachment_ids', 'in', self.ids)])

        return {
            'type': 'ir.actions.act_window',
            'name': self.env._("Deliveries of %s", self.name),
            'res_model': 'stock.picking',
            'view_mode': 'list',
            'views': [(self.env.ref('stock.vpicktree').id, 'list')],
            'domain': [('id', 'in', deca_pickings.ids)],
            'target': 'new',
            'context': {'create': False},
        }
