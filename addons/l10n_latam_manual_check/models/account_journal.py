from odoo import fields, models


class AccountJournal(models.Model):

    _inherit = 'account.journal'

    use_checkbooks = fields.Boolean()
    checkbook_ids = fields.One2many('account.checkbook', 'journal_id', 'Checkbooks', context={'active_test': False},)
