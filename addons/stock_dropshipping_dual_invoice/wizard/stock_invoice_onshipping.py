#    Author: Leonardo Pistone
#    Copyright 2015 Camptocamp SA
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

from openerp import models, api, fields
from openerp.tools.translate import _


class StockInvoiceOnshipping(models.TransientModel):
    _inherit = "stock.invoice.onshipping"

    def _default_second_journal(self):
        res = self.env['account.journal'].search([('type', '=', 'sale')])
        return res and res[0] or False

    def _default_need_two_invoices(self):
        if 'active_id' in self.env.context:
            pick = self.env['stock.picking'].browse(self.env.context['active_id'])
            so = pick.sale_id
            po = pick.move_lines[0].purchase_line_id.order_id
            if so.order_policy == 'picking' and po.invoice_method == 'picking':
                return True

        return False

    @api.depends('invoice_type', 'need_two_invoices')
    def _compute_get_wizard_title(self):
        if self.need_two_invoices:
            self.wizard_title = _("Create Supplier Bill and Customer Invoice")
        else:
            selection = dict(self.fields_get()['invoice_type']['selection'])
            invoice_type = self._get_invoice_type()
            self.wizard_title = selection[invoice_type]

    @api.multi
    def open_invoice(self):
        action_data = super(StockInvoiceOnshipping, self).open_invoice()
        if self.need_two_invoices:
            # Do not show the two invoices, because a form view would be wrong
            return True
        else:
            return action_data

    @api.multi
    def create_invoice(self):
        self.ensure_one()
        if self.need_two_invoices:
            pick_ids = self.env.context['active_ids']
            pick = self.env['stock.picking'].browse(pick_ids)

            # Supplier invoice
            pick_context_in = pick.with_context(partner_to_invoice_id=pick.partner_id.id, date_inv=self.invoice_date)
            first_invoice_ids = pick_context_in.action_invoice_create(
                journal_id=self.journal_id.id, group=self.group, type='in_invoice', move_invoiced=False)
            # Customer invoice
            pick_context_out = pick.with_context(date_inv=self.invoice_date)
            second_invoice_ids = pick_context_out.action_invoice_create(
                journal_id=self.second_journal_id.id, group=self.group, type='out_invoice')

            return first_invoice_ids + second_invoice_ids
        else:
            return super(StockInvoiceOnshipping, self).create_invoice()

    need_two_invoices = fields.Boolean('Need two invoices', default=_default_need_two_invoices)
    second_journal_id = fields.Many2one('account.journal', 'Destination Journal (Customer Invoice)',
                                        default=_default_second_journal)
    wizard_title = fields.Char('Wizard Title', compute='_compute_get_wizard_title', readonly=True)
