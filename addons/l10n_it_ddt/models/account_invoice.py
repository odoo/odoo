# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    def _get_ddt_values(self):
        ddt_dict = {}
        line_count = 1
        for line in self.invoice_line_ids.filtered(lambda l: not l.display_type):
            for picking in line.picking_ids:
                if picking not in ddt_dict:
                    ddt_dict[picking] = []
                ddt_dict[picking].append(line_count)
            line_count += 1
        # ddt_dict have a multiple records of picking and this for loop will check that record same or not in invoice line.
        for picking in ddt_dict:
            if len(ddt_dict[picking]) == line_count-1:
                ddt_dict[picking] = []
        return ddt_dict

    def _export_as_xml(self, template_values):
        template_values['ddt_dict'] = self._get_ddt_values()
        content = self.env.ref('l10n_it_edi.account_invoice_it_FatturaPA_export').render(template_values)
        return content


class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    picking_ids = fields.Many2many(
        'stock.picking', compute='_compute_pickings', string="Pickings")

    def _compute_pickings(self):
        for line in self:
            line.picking_ids = line.sale_line_ids.mapped('move_ids.picking_id')
