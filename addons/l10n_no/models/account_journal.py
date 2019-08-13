# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    invoice_reference_model = fields.Selection(selection_add=[('no', 'Norway')])
