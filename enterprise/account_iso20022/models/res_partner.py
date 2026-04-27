# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import _, api, fields, models
from odoo.exceptions import UserError

LEI_REGEX = '[A-Z0-9]{18,18}[0-9]{2,2}'


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # at the moment it's not mandatory but will be in the future
    iso20022_lei = fields.Char(
        string='LEI',
        help='Legal Entity Identifier',
    )

    @api.constrains('iso20022_lei')
    def _check_iso20022_lei(self):
        for partner in self:
            if partner.iso20022_lei and not re.match(LEI_REGEX, partner.iso20022_lei):
                raise UserError(_("The LEI number must contain 20 characters and match the following structure:\n"
                                  "- 18 alphanumeric characters with capital letters\n"
                                  "- 2 digits in the end\n"))
