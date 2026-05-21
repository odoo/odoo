# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import _, fields, models
from odoo.exceptions import RedirectWarning, UserError

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
            raise UserError(_("Product must have a name to search for a tax category."))

        company = self.env.company
        if not company.l10n_cn_baiwang_app_key:
            raise UserError(_("Baiwang API credentials are not configured. Go to Settings > Accounting > China EDI."))

        client = BaiwangClient(company)

        # Call bizinfo search API
        body = {
            'taxNo': client.tax_no,
            'data': {'keyword': self.name},
        }

        try:
            response = client.call_api('baiwang.bizinfo.search', body, version='6.0')
        except Exception as e:
            raise UserError(_("API error: %s", str(e)))

        if response.get('success'):
            recommendations = response.get('response', [])
            if recommendations:
                best_match = recommendations[0]
                self.l10n_cn_tax_category_code = best_match.get('taxCode')
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Success'),
                        'message': _('Assigned Code: %s', self.l10n_cn_tax_category_code),
                        'type': 'success',
                        'sticky': False,
                    },
                }
            raise UserError(_("Baiwang could not find any matching tax codes for this product name."))
        else:
            err = response.get('errorResponse', {})
            raise UserError(_("Baiwang API error: %s", err.get('message', 'Unknown')))
