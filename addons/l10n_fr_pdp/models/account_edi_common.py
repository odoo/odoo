from odoo import models
from odoo.tools import html2plaintext

PAID_STATES = frozenset({'in_payment', 'paid'})


class AccountEdiCommon(models.AbstractModel):
    _inherit = "account.edi.common"

    def _get_default_notes(self, vals):
        invoice = vals['invoice']
        company = vals['company']
        # Mandatory / default notes for French e-invoicing [BR-FR-05]
        # Only add them when using PDP
        if not company._peppol_is_french_company():
            return {}
        payment_term = invoice.invoice_payment_term_id
        return {
            'PMT': self.env._
                ("In the event of late payment, a flat-rate fee of €40 for collection costs will be charged (Articles L.441-10 and D.441-5 of the Code de commerce)."),
            'PMD': self.env._
                ("Late payment penalties at an annual rate of 10% are applied if the payment is made after the due date."),
            'AAB': html2plaintext(payment_term.note) if payment_term.early_discount else self.env._
                ("No discount for early payment."),
        }

    def _l10n_fr_pdp_get_profile_id(self, vals):
        invoice = vals['invoice']
        # Les valeurs autorisées pour le Cadre (Mode de Facturation) sont:
        # B1 : Dépôt d'une facture de bien
        # S1 : Dépôt d'une facture de prestation de service
        # M1 : Dépôt d'une facture double (livraison de bien et services qui ne sont pas accessoires l'une de l'autre)
        # B2 : Dépôt d'une facture de bien déjà payée
        # S2 : Dépôt d'une facture de prestation de service déjà payée
        # M2 : Dépôt d'une facture double déjà payée
        # B4 : Dépôt d'une facture définitive (après acompte) de bien
        # S4 : Dépôt d'une facture définitive (après acompte) de service
        # M4 : Dépôt d'une facture définitive (après acompte) double
        # S5 : Dépôt par un sous-traitant d'une facture de prestation de service
        # S6 : Dépôt par un cotraitant d'une facture de prestation de service
        # B7 : Dépôt d'une facture de bien ayant fait l'objet d'un e-reporting (TVA déjà collectée)
        # S7 : Dépôt d'une facture de prestation de service ayant fait l'objet d'un e-reporting (TVA déjà collectée)

        tax_scopes = set(invoice.invoice_line_ids.tax_ids.mapped('tax_scope'))
        profile_scope = "B"
        if {'service', 'consu'}.issubset(tax_scopes):
            profile_scope = "M"
        elif 'service' in tax_scopes:
            profile_scope = "S"

        profile_number = "1"
        if invoice.payment_state in PAID_STATES:
            # Already paid
            profile_number = "2"
        elif not invoice._is_downpayment() and invoice.invoice_line_ids._get_downpayment_lines():
            # After downpayment
            profile_number = "4"

        profile_id = f"{profile_scope}{profile_number}"
        return profile_id
