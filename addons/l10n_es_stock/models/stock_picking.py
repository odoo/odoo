# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    country_code = fields.Char(related='company_id.account_fiscal_country_id.code')

    # Every DeCA an attachment linked with Many2many to picking to show a history
    l10n_es_deca_attachment_ids = fields.Many2many(
        comodel_name='ir.attachment',
        relation='l10n_es_deca_picking_attachment_rel',
        column1='picking_id',
        column2='attachment_id',
        string="DeCA",
        copy=False,
    )

    def action_l10n_es_print_deca(self):
        pickings = self.filtered(lambda p: p.picking_type_code == 'outgoing')
        if not pickings:
            raise UserError(self.env._("The DeCA can only be printed for deliveries."))

        draft_pickings = pickings.filtered(lambda p: p.state in ('draft', 'cancel'))
        if draft_pickings:
            raise UserError(self.env._(
                "The DeCA cannot be printed for draft or cancelled deliveries: %(picking_names)s",
                picking_names=', '.join(draft_pickings.mapped('name')),
            ))

        return {
            'type': 'ir.actions.act_window',
            'name': self.env._("Generate DeCA"),
            'res_model': 'l10n_es.deca.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_picking_ids': pickings.ids},
        }
