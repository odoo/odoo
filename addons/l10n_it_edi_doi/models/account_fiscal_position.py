# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _
from odoo.exceptions import UserError


class AccountFiscalPosition(models.Model):
    _inherit = 'account.fiscal.position'

    @api.ondelete(at_uninstall=False)
    def _never_unlink_declaration_of_intent_fiscal_position(self):
        for fiscal_position in self:
            if fiscal_position == fiscal_position.company_id.l10n_it_edi_doi_fiscal_position_id:
                raise UserError(_('You cannot delete the special fiscal position for Declarations of Intent.'))
