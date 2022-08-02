# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    l10n_th_company_info = fields.Selection(
        [('headquarter', 'Headquarter'), ('branch', 'Branch')],
        "Company Information")
    l10n_th_branch_number = fields.Char("Branch Number")
