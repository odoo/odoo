from odoo import _, models


class AccountEdiFormat(models.Model):
    _inherit = 'account.edi.format'

    def _l10n_sa_check_seller_missing_info(self, invoice):  # Override of l10n_sa_edi function
        """
            Helper function to check if ZATCA mandated partner fields are missing for the seller
        """
        partner_id = invoice.company_id.partner_id.commercial_partner_id
        fields_to_check = [
            ('l10n_sa_edi_building_number', _('Building Number for the Buyer is required on Standard Invoices')),
            ('street2', _('Neighborhood for the Seller is required on Standard Invoices')),
            ('l10n_sa_additional_identification_scheme',
             _('Additional Identification Scheme is required for the Seller, and must be one of CRN, MOM, MLS, SAG or OTH'),
             lambda p, v: v in ('CRN', 'MOM', 'MLS', 'SAG', 'OTH')
             ),
            ('l10n_sa_additional_identification_number',
             _('Additional Identification Number is required for the Seller.'),
             lambda p, v: p.l10n_sa_additional_identification_scheme == 'TIN'
             ),
            ('vat',
             _('VAT is required when Identification Scheme is set to Tax Identification Number'),
             lambda p, v: p.l10n_sa_additional_identification_scheme != 'TIN'
             ),
            ('state_id', _('State / Country subdivision'))
        ]
        if invoice.company_id.l10n_sa_use_branch_crn:  # Special Checks when using branch crn
            return self._l10n_sa_check_journal_missing_info(invoice, fields_to_check)

        return self._l10n_sa_check_partner_missing_info(partner_id, fields_to_check)

    def _l10n_sa_check_journal_missing_info(self, invoice, fields_to_check):
        """
            Helper function to check if Journal CRN is populated if branch CRN is enabled
        """
        missing = []
        partner_id = invoice.company_id.partner_id.commercial_partner_id
        journal_id = invoice.journal_id
        fields_to_check.pop(2)
        fields_to_check.pop(2)
        if not journal_id.l10n_sa_branch_crn:
            missing.append(_(f"The Branch CRN on {journal_id.name} needs to be set. Otherwise, you need set the Identification Scheme\
                and Identification Number on {invoice.company_id.name} to be either CRN, MOM, MLS, SAG, or OTH"))

        return missing + self._l10n_sa_check_partner_missing_info(partner_id, fields_to_check)
