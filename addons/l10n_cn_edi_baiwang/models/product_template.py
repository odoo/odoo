# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models
from odoo import models, fields, api
from odoo.exceptions import UserError
from .baiwang_client import BaiwangClient


class ProductTemplate(models.Model):
    """
    These codes are required by the API. They represent the product classifications that are used in China.
    As defined in the list of codes allowed here: https://sdk.myinvois.hasil.gov.my/codes/classification-codes/
    """
    _inherit = "product.template"

    # ------------------
    # Fields declaration
    # ------------------

    l10n_cn_tax_category_code = fields.Char(
        string="Tax Category Code",
        help="19-digit official Golden Tax classification code.",
        copy=False
    )

    def action_fetch_baiwang_tax_code(self):
        """Calls baiwang.bizinfo.search to auto-fill the tax category code."""
        self.ensure_one()

        if not self.name:
            raise UserError("Product must have a name to search for a tax category.")

        company = self.env.company

        # In a real scenario, you would retrieve this dynamically via the orgAuthCode
        token = company.l10n_cn_baiwang_cached_token

        if not token:
            raise UserError("Baiwang API Token is missing. Please authenticate first.")

        client = BaiwangClient(
            app_key=company.l10n_cn_baiwang_app_key,
            app_secret=company.l10n_cn_baiwang_app_secret,
            salt=company.l10n_cn_baiwang_salt,
        )

        # Construct the payload for bizinfo.search
        request_data = {
            "keyword": self.name
        }

        # Execute the call
        response = client.call_api("baiwang.bizinfo.search", request_data, token)

        if response.get("success"):
            # Baiwang returns a list of recommendations. We take the first (highest probability)
            recommendations = response.get("response", [])

            if recommendations:
                best_match = recommendations[0]
                self.l10n_cn_tax_category_code = best_match.get("taxCode")

                # Optional: Show a quick success notification to the user
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Success',
                        'message': f'Assigned Code: {self.l10n_cn_tax_category_code} (Prob: {best_match.get("prob", "N/A")})',
                        'type': 'success',
                        'sticky': False,
                    }
                }
            else:
                raise UserError("Baiwang could not find any matching tax codes for this product name.")
        else:
            error_msg = response.get("errorResponse", {}).get("message", "Unknown API Error")
            raise UserError(f"Baiwang API Rejected Request: {error_msg}")
