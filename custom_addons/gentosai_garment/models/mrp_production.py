# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models
from odoo.exceptions import UserError


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    garment_stage = fields.Selection(
        [
            ('pending', 'Pending'),
            ('cutting', 'Cutting'),
            ('sewing', 'Sewing'),
            ('finishing', 'Finishing'),
            ('packing', 'Packing'),
            ('done', 'Done'),
        ],
        string='Garment Stage',
        default='pending',
        copy=False,
        tracking=True,
        required=True,
    )

    def action_advance_garment_stage(self):
        self.ensure_one()
        if self.state not in ('confirmed', 'progress', 'to_close'):
            raise UserError(_('Garment stage can advance only after confirmation.'))

        stages = ('pending', 'cutting', 'sewing', 'finishing', 'packing', 'done')
        if self.garment_stage == 'done':
            raise UserError(_('Garment workflow is already complete.'))

        self.garment_stage = stages[stages.index(self.garment_stage) + 1]
        return True
