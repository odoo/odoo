# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    documents_account_settings = fields.Boolean()
    account_folder = fields.Many2one('documents.folder', string="Accounting Workspace", check_company=True,
                                     default=lambda self: self.env.ref('documents.documents_finance_folder',
                                                                       raise_if_not_found=False)
                                     )
