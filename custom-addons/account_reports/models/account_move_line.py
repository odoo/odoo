# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

from odoo.exceptions import UserError

class AccountMoveLine(models.Model):
    _name = "account.move.line"
    _inherit = "account.move.line"

    expected_pay_date = fields.Date('Expected Date',
                                    help="Expected payment date as manually set through the customer statement"
                                         "(e.g: if you had the customer on the phone and want to remember the date he promised he would pay)")

    @api.constrains('tax_ids', 'tax_tag_ids')
    def _check_taxes_on_closing_entries(self):
        for aml in self:
            if aml.move_id.tax_closing_end_date and (aml.tax_ids or aml.tax_tag_ids):
                raise UserError(_("You cannot add taxes on a tax closing move line."))
