# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import fields, api, models

CHECK_VAT_PH_RE = re.compile(r"\d{3}-\d{3}-\d{3}-\d{5}")

class ResPartner(models.Model):
    _inherit = "res.partner"

    branch_code = fields.Char("Branch Code", default='000', required=True)
    first_name = fields.Char("First Name")
    middle_name = fields.Char("Middle Name")
    last_name = fields.Char("Last Name")

    @api.model
    def _commercial_fields(self):
        return super()._commercial_fields() + ['branch_code']

<<<<<<< HEAD
    def check_vat_ph(self, vat):
        return len(vat) == 17 and CHECK_VAT_PH_RE.match(vat)
||||||| parent of 59624029c1a (temp)
    @api.depends('vat', 'country_id')
    def _compute_branch_code(self):
        for partner in self:
            branch_code = '000'
            if partner.country_id.code == 'PH':
                match = partner.__check_vat_ph_re.match(partner.vat)
                branch_code = match and match.group(1) and match.group(1)[1:] or branch_code
            partner.branch_code = branch_code
=======
    @api.depends('vat', 'country_id')
    def _compute_branch_code(self):
        for partner in self:
            branch_code = '000'
            if partner.country_id.code == 'PH' and partner.vat:
                match = partner.__check_vat_ph_re.match(partner.vat)
                branch_code = match and match.group(1) and match.group(1)[1:] or branch_code
            partner.branch_code = branch_code
>>>>>>> 59624029c1a (temp)
