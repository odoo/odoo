# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_au_branch_code = fields.Char(
        string="Branch Code",
        help="The branch code of the company, if any.")
    l10n_au_wpn_number = fields.Char(
        string="Withholding Payer Number",
        help="Number given to individuals / enterprises that have PAYGW obligations but don't have an ABN.")
    l10n_au_registered_for_whm = fields.Boolean("Registered for Working Holiday Maker")
    l10n_au_registered_for_palm = fields.Boolean("Registered for PALM Scheme")

    l10n_au_previous_bms_id = fields.Char("Previous BMS ID")
    l10n_au_bms_id = fields.Char("BMS ID", readonly=False)
