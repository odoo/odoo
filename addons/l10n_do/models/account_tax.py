# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class AccountTax(models.Model):
    _inherit = 'account.tax'

    l10n_do_isr_type = fields.Selection(
        string="ISR Withholding Type",
        help="Type of ISR withholding, as expected on the DGII 606 report",
        selection=[
            ('1', "1 - Rentals"),
            ('2', "2 - Service Fees"),
            ('3', "3 - Other Income"),
            ('4', "4 - Other Income (Presumed Income)"),
            ('5', "5 - Interest Paid to Resident Legal Entities"),
            ('6', "6 - Interest Paid to Resident Individuals"),
            ('7', "7 - Withholding to State Suppliers"),
            ('8', "8 - Telephone Games"),
            ('9', "9 - Bovine Meat Livestock Subsector Withholdings"),
        ],
    )
