from odoo import _, api, fields, models


class FidelityBalance(models.Model):
    _name = 'fidelity.balance'
    _description = "Fidelity Balance"

    card_id = fields.Many2one('fidelity.card', index=True, required=True, ondelete='cascade', readonly=True)
    partner_id = fields.Many2one(related='card_id.partner_id', store=True, readonly=True)
    program_id = fields.Many2one('fidelity.program', index=True, required=True, ondelete='cascade', readonly=True)
    transaction_ids = fields.One2many('fidelity.transaction', 'balance_id', string="Transactions", readonly=True)
    nb_transactions = fields.Integer(string="Usage", compute="_compute_nb_transactions", readonly=True)
    point_unit = fields.Char(related='program_id.point_unit', readonly=True)
    balance = fields.Integer(compute="_compute_balance", readonly=True)
    balance_display = fields.Char(string="Balance", compute="_compute_balance_display", readonly=True)

    @api.depends('balance', 'point_unit')
    def _compute_balance_display(self):
        for record in self:
            record.balance_display = f"{record.balance} {record.point_unit}"

    @api.constrains('transaction_ids')
    def _check_transactions_belong_to_balance_program(self):
        for record in self:
            programs = record.transaction_ids.mapped('program_id')
            if len(programs) > 1 or (len(programs) == 1 and programs[0] != record.program_id):
                raise ValueError(_("All transactions linked to a fidelity balance must belong to the same program as the balance."))

    @api.depends('transaction_ids', 'transaction_ids.issued', 'transaction_ids.used')
    def _compute_balance(self):
        for record in self:
            issued_points = sum(record.transaction_ids.mapped('issued'))
            used_points = sum(record.transaction_ids.mapped('used'))
            record.balance = issued_points - used_points

    @api.depends('transaction_ids')
    def _compute_nb_transactions(self):
        for record in self:
            record.nb_transactions = len(record.transaction_ids)
