# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_de_nat_tax_nb = fields.Char(string="National Tax ID")  # This is not the vat
