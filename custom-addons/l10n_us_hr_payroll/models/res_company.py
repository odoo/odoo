# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_us_ca_ett_tax = fields.Boolean(
        string="California: ETT Tax",
        default=True,
        help="Employment Training Tax (ETT) it is charged to companies depending on a specific reserve account. If their UI reserve account balance is positive (zero or greater), they pay an ETT of 0.1 percent. If they have a negative UI reserve account balance, they do not pay ETT and it is shown as 0.0 percent on the notice.")
