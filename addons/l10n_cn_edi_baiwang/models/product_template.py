# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models
from odoo.exceptions import UserError

from .baiwang_client import BaiwangClient


class ProductTemplate(models.Model):
    _inherit = "product.template"

    # ------------------
    # Fields declaration
    # ------------------

    l10n_cn_tax_category_code = fields.Char(
        string="Tax Category Code",
        help="19-digit official Golden Tax classification code (税收分类编码).",
        copy=False,
    )

    def action_fetch_baiwang_tax_code(self):
        """Calls baiwang.bizinfo.search to auto-fill the tax category code."""
        self.ensure_one()

        if not self.name:
            raise UserError(self.env._("Product must have a name to search for a tax category."))

        company = self.env.company
        if not company.l10n_cn_baiwang_app_key:
            raise UserError(self.env._("Baiwang API credentials are not configured. Go to Settings > Invoicing > China Electronic Invoicing (Baiwang)."))

        client = BaiwangClient(company)
        client.ensure_connection()

        # Call bizinfo search API
        body = {
            'taxNo': client.tax_no,
            'data': {'keyword': self.name},
        }

        response = client.call_api('baiwang.bizinfo.search', body, version='6.0')

        if response.get('success'):
            recommendations = response.get('response', [])
            if recommendations:
                best_match = recommendations[0]
                self.l10n_cn_tax_category_code = best_match.get('taxCode')
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': self.env._('Success'),
                        'message': self.env._('Assigned Code: %s', self.l10n_cn_tax_category_code),
                        'type': 'success',
                        'sticky': False,
                    },
                }
            raise UserError(self.env._("Baiwang could not find any matching tax codes for this product name."))
        err = response.get('errorResponse', {})
        error_message = err.get('message', 'Unknown')
        sub_code = err.get('subCode')
        sub_message = err.get('subMessage')
        details = []
        if sub_code:
            details.append(self.env._("Sub-code: %s", sub_code))
        if sub_message:
            details.append(self.env._("Details: %s", sub_message))
        if details:
            raise UserError(self.env._("Baiwang API error: %s\n%s", error_message, "\n".join(details)))
        raise UserError(self.env._("Baiwang API error: %s", error_message))
