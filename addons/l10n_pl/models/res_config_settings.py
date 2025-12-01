# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_pl_reports_tax_office_id = fields.Many2one(related='company_id.l10n_pl_reports_tax_office_id', readonly=False)
    #group_only_poland = fields.Boolean("Only visible fo polish companies", implied_group='l10n_pl_reports.group_only_poland', default=True)