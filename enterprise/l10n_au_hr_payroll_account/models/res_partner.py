# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _
from odoo.exceptions import UserError


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.ondelete(at_uninstall=False)
    def _unlink_except_clearing_house(self):
        clearing_house = self.env.ref(
            "l10n_au_hr_payroll_account.res_partner_clearing_house",
            raise_if_not_found=False,
        )
        if clearing_house and clearing_house in self:
            raise UserError(
                _(
                    "You cannot delete this Contact (%s), it is used for superstream clearning house.",
                    clearing_house.name,
                )
            )
