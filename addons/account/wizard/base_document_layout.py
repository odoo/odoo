from odoo import models


class BaseDocumentLayout(models.TransientModel):
    _inherit = 'base.document.layout'

    def document_layout_save(self):
        res = super(BaseDocumentLayout, self).document_layout_save()
        for wizard in self:
            wizard.company_id.action_save_onboarding_invoice_layout()
        return res
