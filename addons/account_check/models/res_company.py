##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models, _
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = 'res.company'

    rejected_check_account_id = fields.Many2one(
        'account.account',
        'Rejected Checks Account',
        help='Rejection Checks account, for eg. "Rejected Checks"',
    )
    deferred_check_account_id = fields.Many2one(
        'account.account',
        'Deferred Checks Account',
        help='Deferred Checks account, for eg. "Deferred Checks"',
    )
    holding_check_account_id = fields.Many2one(
        'account.account',
        'Holding Checks Account',
        help='Holding Checks account for third checks, '
        'for eg. "Holding Checks"',
    )

    def _get_check_account(self, check_type):
        self.ensure_one()
        if check_type == 'holding':
            account = self.holding_check_account_id
        elif check_type == 'rejected':
            account = self.rejected_check_account_id
        elif check_type == 'deferred':
            account = self.deferred_check_account_id
        else:
            raise UserError(_("Check type %s not implemented!") % check_type)
        if not account:
            raise UserError(_(
                'No checks %s account defined for company %s'
            ) % (check_type, self.name))
        return account
