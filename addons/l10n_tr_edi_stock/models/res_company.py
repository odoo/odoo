from odoo import models


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _l10n_tr_edi_dispatch_enabled(self):
        """Return whether the company's e-Document provider exchanges e-Dispatches.

        Provider modules override this for their own provider.
        """
        self.ensure_one()
        return False
