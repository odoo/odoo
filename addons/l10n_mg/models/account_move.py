from markupsafe import Markup

from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _get_document_partner_ident_line(self) -> str:
        # EXTENDS 'account'
        # CPF art. IV-21: invoices show the NIF and the statistical number (STAT) of the customer
        partner = self.partner_id.commercial_partner_id
        if (
            self.company_id.account_fiscal_country_id.code != "MG"
            or partner.country_code != "MG"
        ):
            return super()._get_document_partner_ident_line()
        # Legal acronyms, the same in all languages
        identifiers = [
            ("NIF", partner._l10n_mg_get_nif()),
            ("STAT", partner._get_additional_identifier("MG_STAT")),
        ]
        return Markup("<br/>").join(
            f"{label}: {value}" for label, value in identifiers if value
        )
