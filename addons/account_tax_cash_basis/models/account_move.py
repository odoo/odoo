# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class AccountMoveCashBasis(models.Model):
    _inherit = 'account.move'

    tax_cash_basis_rec_id = fields.Many2one(
        'account.partial.reconcile',
        string='Tax Cash Basis Entry of',
        help="Technical field used to keep track of the tax cash basis reconciliation."
        "This is needed when cancelling the source: it will post the inverse journal entry to cancel that part too.")
