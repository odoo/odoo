from odoo import models


class ResCompany(models.Model):

    _inherit = "res.company"

    def _compute_company_vat_placeholder(self):
        """
        To set the placeholder for the VAT field in companies located in Ecuador (EC),
        For Ecuadorian companies the vat is a 13-digit number (RUC)
        """
        companies_ec = self.filtered(lambda c: c.country_id.code == "EC")
        placeholder = '0123456789001'
        for company in companies_ec:
            company.company_vat_placeholder = placeholder

        super(ResCompany, self - companies_ec)._compute_company_vat_placeholder()

    def _localization_use_documents(self):
        self.ensure_one()
        return self.account_fiscal_country_id.code == "EC" or super(ResCompany, self)._localization_use_documents()
