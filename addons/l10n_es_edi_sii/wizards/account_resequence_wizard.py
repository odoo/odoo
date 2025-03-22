# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class AccountResequenceWizard(models.TransientModel):
    _inherit = "account.resequence.wizard"

    def _frozen_edi_documents(self):
        docs = super()._frozen_edi_documents()
        # SII vendor bills are sent with ref, so they can be resequenced
        return docs.filtered(
            lambda doc: doc.edi_format_id.code != "es_sii"
            or doc.move_id.is_sale_document()
        )
