# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_us_adp_code = fields.Char("ADP code",
                           groups="hr.group_hr_user")
