# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, api
from odoo.addons.purchase.models.res_partner_bank import FrontendFieldSpec


class ResPartnerBank(models.Model):
    _inherit = "res.partner.bank"

    @api.model
    def _get_frontend_bank_account_fields(self):
        """Override."""
        res = super()._get_frontend_bank_account_fields()
        us = self.env.ref("base.us").id
        res.extend(
            [
                FrontendFieldSpec(
                    country_id=us,
                    type="text",
                    name="aba_routing",
                    label="ABA/Routing",
                    required=True,
                    placeholder="121000358",
                ),
                FrontendFieldSpec(
                    country_id=us, type="file", name="w9", label="Taxpayer identification (W9)", required=False
                ),
            ]
        )
        return res
