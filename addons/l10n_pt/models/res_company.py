# -*- coding: utf-8 -*-
from odoo import fields, models, _, api


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_pt_account_region_code = fields.Char(compute='_compute_l10n_pt_region_code', store=True, readonly=False)

    @api.depends('country_id', 'state_id')
    def _compute_l10n_pt_region_code(self):
        for company in self.filtered(lambda c: c.country_id.code == 'PT'):
            if company.state_id == self.env.ref('base.state_pt_pt-20'):
                company.l10n_pt_account_region_code = 'PT-AC'
            elif company.state_id == self.env.ref('base.state_pt_pt-30'):
                company.l10n_pt_account_region_code = 'PT-MA'
            else:
                company.l10n_pt_account_region_code = 'PT'
