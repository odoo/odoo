# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrTimeRuleAllocationLog(models.Model):
    _name = 'hr.time.rule.allocation.log'
    _description = 'Time Rule Allocation Credit Log'
    # one row per (source record, allocation) credit produced by the engine.
    # used to reverse credits precisely when the source record is modified or deleted.

    source_model = fields.Char(required=True, index='btree_not_null')
    source_id = fields.Integer(required=True, index='btree_not_null')
    # pseudo-reference instead of a real Many2one so the table works for both
    # hr.attendance and hr.leave sources.

    allocation_id = fields.Many2one(
        'hr.leave.allocation', required=True, ondelete='cascade', index=True,
    )
    days = fields.Float(
        required=True,
        help="Net days credited to the allocation from this source record."
             "Positive = excess credit added; negative = deficit deduction applied."
    )
