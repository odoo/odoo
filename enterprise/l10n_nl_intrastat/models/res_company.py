# -*- coding: utf-8 -*-

from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_nl_cbs_reg_number = fields.Char(string='Registration Number', size=6)
