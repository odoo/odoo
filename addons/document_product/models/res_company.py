from odoo import api, fields, models
from odoo.fields import Domain


class ResCompany(models.Model):
    _inherit = "res.company"

    document_product_config_id = fields.Many2one(
        comodel_name="document_product.config",
        compute="_compute_document_product_config_id",
        search="_search_document_product_config_id",
    )

    def _search_document_product_config_id(self, operator, value):
        return self._search_config_link("document_product.config", operator, value)

    def _compute_document_product_config_id(self):
        configs = self.env["document_product.config"]._for_each(self)
        by_company = dict(zip(configs.mapped("company_id").ids, configs, strict=True))
        for company in self:
            company.document_product_config_id = by_company.get(company.id, False)

    @api.model
    def _get_domain_used_folder_ids(self, folder_ids):
        return super()._get_domain_used_folder_ids(folder_ids) | Domain(
            "document_product_config_id",
            "any",
            Domain("product_folder_id", "in", folder_ids)
            & Domain("documents_product_settings", "=", True),
        )
