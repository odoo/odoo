# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template("ph", "l10n_ph.discount.privilege")
    def _get_ph_discount_privileges(self):
        return {
            "l10n_ph_discount_privilege_sc_20_vat_incl": {
                "name": "20% Senior Citizen Discount",
                "discount_type": "sc",
                "discount_amount": 0.2,
                "fiscal_position_id": "l10n_ph_fiscal_position_discount_privileges",
                "account_id": "l10n_ph_account_401021",
            },
            "l10n_ph_discount_privilege_pwd_20_vat_incl": {
                "name": "20% PWD Discount",
                "discount_type": "pwd",
                "discount_amount": 0.2,
                "fiscal_position_id": "l10n_ph_fiscal_position_discount_privileges",
                "account_id": "l10n_ph_account_401022",
            },
            "l10n_ph_discount_privilege_sc_5": {
                "name": "5% Senior Citizen Discount",
                "discount_type": "special",
                "discount_amount": 0.05,
                "account_id": "l10n_ph_account_401021",
            },
        }
