# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_ro_is_self_invoice = fields.Boolean(
        string='Is self invoice?',
        help='Check this box to indicate that this bill is a self-invoice made to register '
             'a VAT event in the absence of an invoice received from a supplier.',
    )
