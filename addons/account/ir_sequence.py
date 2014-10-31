# -*- coding: utf-8 -*-

from openerp import models, fields, api


class ir_sequence_fiscalyear(models.Model):
    _name = 'account.sequence.fiscalyear'
    _rec_name = "sequence_main_id"

    sequence_id = fields.Many2one('ir.sequence', string='Sequence', required=True,
        ondelete='cascade')
    sequence_main_id = fields.Many2one('ir.sequence', string='Main Sequence',
        required=True, ondelete='cascade')
    fiscalyear_id = fields.Many2one('account.fiscalyear', string='Fiscal Year',
        required=True, ondelete='cascade')

    _sql_constraints = [
        ('main_id', 'CHECK (sequence_main_id != sequence_id)', 'Main Sequence must be different from current !'),
    ]


class ir_sequence(models.Model):
    _inherit = 'ir.sequence'

    fiscal_ids = fields.One2many('account.sequence.fiscalyear', 'sequence_main_id', string='Sequences', copy=True)

    @api.multi
    def _next(self):
        context = dict(self._context or {})
        for seq in self:
            for line in seq.fiscal_ids:
                if line.fiscalyear_id.id == context.get('fiscalyear_id'):
                    return super(ir_sequence, self)._next([line.sequence_id.id])
        return super(ir_sequence, self)._next()
