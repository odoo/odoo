# -*- coding: utf-8 -*-

from odoo import models, fields, api

class IrView(models.Model):
    _inherit = 'ir.ui.view'

    l10n_mx_edi_addenda_flag = fields.Boolean(
        string='Is an addenda?',
        help='Is a view representing an addenda for the Mexican EDI invoicing.',
        default=False,
        stored=True)