from odoo import _, api, models
from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class AccountTax(models.Model):
    _inherit = "account.tax"

    @api.ondelete(at_uninstall=False)
    def _never_unlink_declaration_of_intent_tax(self):
        for tax in self:
            if tax in tax.company_ids.l10n_it_edi_doi_tax_id:
                _debug.logic("doi_tax_protected", taxes=self)
                raise UserError(
                    _("You cannot delete the special tax for Declarations of Intent.")
                )
