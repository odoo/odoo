# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields
from odoo.addons import l10n_latam_check


class AccountPayment(l10n_latam_check.AccountPayment):


    l10n_ar_withholding_ids = fields.One2many(related='move_id.l10n_ar_withholding_ids')
