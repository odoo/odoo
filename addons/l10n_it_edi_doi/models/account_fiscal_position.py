from odoo import _, api, models
from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class AccountFiscalPosition(models.Model):
    _inherit = "account.fiscal.position"

    @api.ondelete(at_uninstall=False)
    def _never_unlink_declaration_of_intent_fiscal_position(self):
        for fiscal_position in self:
            if (
                fiscal_position
                == fiscal_position.company_id.l10n_it_edi_doi_fiscal_position_id
            ):
                _debug.logic("doi_fiscal_position_protected", positions=self)
                raise UserError(
                    _(
                        "You cannot delete the special fiscal position for Declarations of Intent."
                    )
                )
