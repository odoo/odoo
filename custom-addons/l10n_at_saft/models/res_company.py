# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_at_oenace_code = fields.Char(
        string="ÖNACE-Code",
        help="ÖNACE-Code (Austrian Version of NACE-classification)")
    l10n_at_profit_assessment_method = fields.Selection(
        selection=[
            ('par_4_abs_1', 'Betriebsvermögensvergleich nach § 4 Abs. 1 EStG'),
            ('par_5', 'Betriebsvermögensvergleich nach § 5 EStG'),
        ],
        string="Profit Assessment Method")
