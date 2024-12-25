from odoo import models


class AccountEdiXmlUBL21Zatca(models.AbstractModel):
    _inherit = "account.edi.xml.ubl_21.zatca"

    def _export_invoice_vals(self, invoice):
        vals = super()._export_invoice_vals(invoice)
        vals['vals']['accounting_supplier_party_vals']['party_vals'].update(
            self._l10n_sa_get_supplier_party_vals(invoice)
        )

        return vals

    def _l10n_sa_get_supplier_party_vals(self, invoice):
        if invoice.journal_id.l10n_sa_use_branch_crn and invoice.journal_id.l10n_sa_branch_crn:
            return {
                'party_identification_vals': [{
                    'id_attrs': {'schemeID': 'CRN'},
                    'id': invoice.journal_id.l10n_sa_branch_crn,
                }]
            }
        return {}
