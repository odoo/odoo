# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = "account.move"

    def _post(self, soft=True):
        """Check state is set in company/sub-unit"""
        for move in self.filtered(lambda m: m.country_code == 'IN'):
            company_unit_partner = move.journal_id.l10n_in_gstin_partner_id or move.journal_id.company_id
            if not company_unit_partner.state_id:
                raise ValidationError(_(
                    "Your company %(company_name)s needs to have a correct\n address in order to validate this invoice.\n"
                    "Set the address of your company \n(Don't forget the State field)",
                    company_name=company_unit_partner.name
                ))

        return super()._post(soft)
