# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_mx_closing_move = fields.Boolean(
        string="Month 13 Closing",
        help="Whether this is a closing entry for the fiscal year that should appear in the Month 13 Trial Balance",
    )

    # This will cause the upgrade to fail if there exists a closing entry with a date different from 31/12.
    # This is intentional as a closing entry should never be made on a date other than 31/12.
    # Solutions:
    # - (Solution 1) remove the 'l10n_mx_closing_move' flag from that entry.
    # - (Solution 2) reset the entry to draft and change the accounting date.
    _sql_constraints = [(
        "l10n_mx_closing_move_on_dec_31",
        "CHECK(DATE_PART('month', date) = 12 AND DATE_PART('day', date) = 31 OR l10n_mx_closing_move = FALSE)",
        "Month 13 closing entries should be done on December 31st."
    )]
