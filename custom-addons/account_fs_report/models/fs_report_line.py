from odoo import fields, models


class FsReportLine(models.Model):
    _name = 'fs.report.line'
    _description = 'Financial Statement Line'
    _order = 'sequence, id'

    report_id = fields.Many2one('fs.report', required=True, ondelete='cascade')
    parent_id = fields.Many2one('fs.report.line', ondelete='cascade')
    child_ids = fields.One2many('fs.report.line', 'parent_id')
    sequence = fields.Integer(default=10)
    code = fields.Char(required=True)
    name = fields.Char(required=True, translate=True)
    formula_type = fields.Selection([
        ('none', 'Header (no value)'),
        ('account_type', 'Account types'),
        ('aggregation', 'Aggregation of line codes'),
        ('current_earnings', 'Current year earnings'),
        ('previous_earnings', 'Previous years unallocated earnings'),
    ], required=True, default='none')
    account_types = fields.Char(help='Comma-separated account_type values')
    aggregation = fields.Char(help='Example: TA-TL')
    sign = fields.Integer(default=1, help='1 keeps debit-credit; -1 flips it')
    unfold_accounts = fields.Boolean(default=True)
    hide_if_zero = fields.Boolean(default=False)
    # Enterprise: action_id on CYE opens P&amp;L and paints the name with .clickable (action color).
    action_id = fields.Many2one('ir.actions.actions', string='Action')
