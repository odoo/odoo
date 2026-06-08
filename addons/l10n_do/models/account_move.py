from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _get_l10n_latam_documents_domain(self):
        self.ensure_one()
        domain = super()._get_l10n_latam_documents_domain()
        if self.country_code != 'DO' or not self.l10n_latam_use_documents:
            return domain
        if self.move_type == 'out_invoice' and not self.debit_origin_id:
            allowed_docs = [self.env.ref('l10n_do.ecf_31').id, self.env.ref('l10n_do.ecf_32').id] if self.partner_id.vat else [self.env.ref('l10n_do.ecf_32').id]
            domain.append(('id', 'in', allowed_docs))
        return domain
