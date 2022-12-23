from odoo import models


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _l10n_sa_get_csr_invoice_type(self):
        """
            Override to add support for simplified invoices
        """
        return '1100'

