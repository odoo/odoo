from odoo import fields, models


class L10nSGStatutoryBoardSubbusinessUnit(models.Model):
    _name = 'l10n.sg.statutory.board.subbusiness.unit'
    _description = 'Statutory Board Sub-Business Unit'

    name = fields.Char(string='Name')
    code = fields.Char(string='Code')
    statutory_board_id = fields.Many2one(
        'res.partner',
        string='Statutory Board',
    )
