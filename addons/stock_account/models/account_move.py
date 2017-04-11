# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields

class AccountMove(models.Model):
    _inherit = 'account.move'

    stock_account_valuation_correction = fields.Boolean(string="Is valuation correction move", default=False, help="True if and only if this account move has been created in order to correct the stock valuation of some product, because of the variations of the currency rates.")
    stock_account_valuation_corrected_qty = fields.Integer(string="Corrected quantity", default=0, help="Quantity of items associated with this account whose valuation has already been corrected by an invoice. Always 0 <= ... <= quantity.")


    def mark_valuation_as_fully_corrected(self):
        """ Marks this account move as a stock valuation having been fully
        corrected by one or more other account moves to match the exact amount
        that had been invoiced (which can be different from the inital one
        because of changes in the currency rates).
        """
        self.stock_account_valuation_corrected_qty = self.quantity