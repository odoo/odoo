from odoo import models


class L10nLatamDocumentType(models.Model):
    _inherit = "l10n_latam.document.type"

    def _l10n_uy_edi_get_move_type(self, journal_type="purchase"):
        """ This method should be moved to latam module in future versions, will be available in 18, is a temporal method here. It is necessary to get the move_type depending on the internal type of the invoice document type. Look at https://github.com/odoo/odoo/pull/140198 """
        self.ensure_one()
        prefix = "in" if journal_type == "purchase" else "out"
        data = {
            "invoice": f"{prefix}_invoice",
            "debit_note":  f"{prefix}_invoice",
            "credit_note":  f"{prefix}_refund",
        }
        return data.get(self.internal_type)
