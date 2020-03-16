# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields


class AccountJournal(models.Model):

    _inherit = 'account.journal'

    invoice_reference_model = fields.Selection(selection_add=[
        ('finnish', 'Finnish Standard Reference'),
        ('finnish_rf', 'Finnish Creditor Reference (RF)'),
    ])
