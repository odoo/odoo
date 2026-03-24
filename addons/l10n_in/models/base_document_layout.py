from odoo import models


class BaseDocumentLayout(models.TransientModel):
    _inherit = 'base.document.layout'

    def _get_footer_fields(self):
        company = self.env.company
        # IN Company footer should not contain phone as it is already present in the company details header.
        if company.country_code == 'IN':
            return [company.phone, company.email, company.website]
        return super()._get_footer_fields()
