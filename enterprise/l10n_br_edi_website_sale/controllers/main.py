# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.website_sale.controllers.main import WebsiteSale as WebsiteSaleController
from odoo.http import request


class WebsiteSale(WebsiteSaleController):
    def _complete_address_values(self, address_values, address_type, use_same, order_sudo):
        """Override. Complete the address for EDI in the B2C case (CPF identification)."""
        super()._complete_address_values(address_values, address_type, use_same, order_sudo)
        if address_values.get("l10n_latam_identification_type_id") == request.env.ref("l10n_br.cpf").id:
            fiscal_position = request.env["account.fiscal.position"].sudo().search([
                ("company_id", "=", order_sudo.company_id.id), ("l10n_br_is_avatax", "=", True)
            ], limit=1)
            address_values.update({
                "property_account_position_id": fiscal_position.id,
                "l10n_br_tax_regime": "individual",
                "l10n_br_taxpayer": "non",
                "l10n_br_activity_sector": "finalConsumer",
                "l10n_br_subject_cofins": "T",
                "l10n_br_subject_pis": "T",
                "l10n_br_is_subject_csll": True,
            })
