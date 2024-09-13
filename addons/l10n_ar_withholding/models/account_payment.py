# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields


class AccountPayment(models.Model):

    _inherit = 'account.payment'

    l10n_ar_withholding_ids = fields.One2many(related='move_id.l10n_ar_withholding_ids')
