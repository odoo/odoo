# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, _

from odoo.exceptions import UserError


class ResCurrency(models.Model):
    _inherit = 'res.currency'

    display_rounding_warning = fields.Boolean(string="Display Rounding Warning", compute='_compute_display_rounding_warning', help="Technical field used to tell whether or not to display the warning informing a rounding factor change might be dangerous on res.currency's form view.")


    @api.depends('rounding')
    def _compute_display_rounding_warning(self):
        for record in self:
            record.display_rounding_warning = record.id \
                                              and record._origin.rounding != record.rounding \
                                              and record._origin._has_accounting_entries()

    def write(self, vals):
        if 'rounding' in vals:
            rounding_val = vals['rounding']
            for record in self:
                if (rounding_val > record.rounding or rounding_val == 0) and record._has_accounting_entries():
                    raise UserError(_("You cannot reduce the number of decimal places of a currency which has already been used to make accounting entries. If you really need to do that, please contact tech support."))

        return super(ResCurrency, self).write(vals)

    def _has_accounting_entries(self):
        """ Returns True iff this currency has been used to generate (hence, round)
        some move lines (either as their foreign currency, or as the main currency
        of their company).
        """
        self.ensure_one()
        return bool(self.env['account.move.line'].search_count(['|', ('currency_id', '=', self.id), ('company_currency_id', '=', self.id)]))

