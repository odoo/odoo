# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.addons import account, base_vat


class ResConfigSettings(base_vat.ResConfigSettings, account.ResConfigSettings):

    l10n_pl_reports_tax_office_id = fields.Many2one(related='company_id.l10n_pl_reports_tax_office_id', readonly=False)
