# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    invoice_reference_model = fields.Selection(selection_add=[
        ('fi', 'Finnish Standard Reference (2024000068)'),
        ('fi_rf', 'Finnish Creditor Reference (RF) (RF952024000071)'),
    ], ondelete={'fi': lambda recs: recs.write({'invoice_reference_model': 'odoo'}),
                 'fi_rf': lambda recs: recs.write({'invoice_reference_model': 'odoo'})})
