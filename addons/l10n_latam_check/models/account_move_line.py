# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons import account
from odoo import fields, models


class AccountMoveLine(models.Model, account.AccountMoveLine):


    l10n_latam_check_ids = fields.One2many('l10n_latam.check', 'outstanding_line_id', string='Checks')
