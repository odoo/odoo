import base64

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    web_config_id = fields.Many2one(
        comodel_name="web.config",
        compute="_compute_web_config_id",
        search="_search_web_config_id",
    )

    def _search_web_config_id(self, operator, value):
        return self._search_config_link("web.config", operator, value)

    def _compute_web_config_id(self):
        configs = self.env["web.config"]._for_each(self)
        by_company = dict(zip(configs.mapped("company_id").ids, configs, strict=True))
        for company in self:
            company.web_config_id = by_company.get(company.id, False)

    def _get_asset_style_b64(self) -> bytes:
        company_ids = self.sudo().search([])
        company_styles = self.env["ir.qweb"]._render(
            "web.styles_company_report",
            {
                "company_ids": company_ids,
            },
            raise_if_not_found=False,
        )
        return base64.b64encode(company_styles.encode())

    def _update_asset_style(self) -> None:
        asset_attachment = self.env.ref(
            "web.asset_styles_company_report", raise_if_not_found=False
        )
        if not asset_attachment:
            return
        asset_attachment = asset_attachment.sudo()
        b64_val = self._get_asset_style_b64()
        if b64_val != asset_attachment.datas:
            asset_attachment.write({"datas": b64_val})
