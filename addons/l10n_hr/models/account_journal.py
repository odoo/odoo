# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    invoice_reference_model = fields.Selection(
        selection_add=[
            ('hr', 'Croatia - HR00(Partner) HR01(Invoice)'),
        ],
        ondelete={
            'hr': lambda recs: recs.write({'invoice_reference_model': 'odoo'}),
        })
