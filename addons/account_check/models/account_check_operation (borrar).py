from odoo import fields, models


class AccountCheckOperation(models.Model):

    _name = 'account.check.operation'
    _description = 'account.check.operation'
    _rec_name = 'operation'
    _order = 'date desc, id desc'

    # TODO this could be related stored?
    date = fields.Date(required=True, index=True)
    check_id = fields.Many2one('account.check', 'Check', required=True, ondelete='cascade', auto_join=True, index=True)
    partner_id = fields.Many2one('res.partner', string='Partner', related='move_line_id.partner_id')
    move_line_id = fields.Many2one('account.move', string='Origin')
    operation = fields.Selection([
        ('holding', 'Receive'),
        ('deposited', 'Collect'),
        ('delivered', 'Deliver'),
        ('withdrawed', 'Withdrawal'),
        ('handed', 'Hand'),
        ('debited', 'Debit'),
        ('returned', 'Return'),
    ],
        required=True,
    )
