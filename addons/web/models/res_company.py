import base64

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    homemenu_default_config = fields.Json(
        string="Default Home Menu Layout",
        help="The home menu layout a user of this company sees until they "
        "customise their own: the same shape as the user's setting.",
    )

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
