# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class IrSequence(models.Model):
    _inherit = 'ir.sequence'

    def _next(self, sequence_date=None):
        """Prevent PSQL calls that cannot be rolled back during test import."""
        if self.implementation == 'standard' and self.env.context.get('import_dryrun'):
            # will be rolled back later
            self.write({
                'number_next': self.number_next_actual,
                'implementation': 'no_gap',
            })
        return super()._next(sequence_date=sequence_date)
