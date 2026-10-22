# Part of Odoo. See LICENSE file for full copyright and licensing details.
from stdnum.se import orgnr as stdnum_se_orgnr

from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    # Deprecated: use partner_id.additional_identifiers['SE_EN'] instead.
    # Kept in stable for compatibility, to be removed in master.
    org_number = fields.Char(compute='_compute_org_number')

    @api.depends('partner_id.additional_identifiers')
    def _compute_org_number(self):
        for company in self:
            org_number = company.partner_id._get_additional_identifier('SE_EN')
            company.org_number = stdnum_se_orgnr.format(org_number) if org_number else ''
