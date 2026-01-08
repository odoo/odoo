from odoo import models


class BaseDocumentLayout(models.TransientModel):
    _inherit = 'base.document.layout'

    def document_layout_save(self):
        """Save layout and onboarding step progress, return super() result"""
        res = super(BaseDocumentLayout, self).document_layout_save()
        if step := self.env.ref('account.onboarding_onboarding_step_base_document_layout', raise_if_not_found=False):
            for company_id in self.company_id:
                step.with_company(company_id).action_set_just_done()
        return res
