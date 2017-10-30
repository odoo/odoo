from openerp import models, api, fields
from openerp.tools.translate import _
from openerp.exceptions import UserError


class AccountBankStatement(models.Model):
    _inherit = 'account.bank.statement'

    # Prevent modifying anything coming from the pos
    # hashing
    # TO DO in master : refactor hashing algo to go into a mixin

    @api.multi
    def write(self, vals):
        pass

    @api.model
    def create(self, vals):
        pass

    def unlink(self):
        pass

