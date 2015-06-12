# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import models, api, fields
from openerp.tools.translate import _


class StockInvoiceOnshipping(models.TransientModel):
    _inherit = "stock.invoice.onshipping"

    @api.model
    def _get_invoice_type(self):
        pick = self.env['stock.picking'].browse(self.env.context['active_id'])
        src_usage = pick.move_lines[0].location_id.usage
        dest_usage = pick.move_lines[0].location_dest_id.usage
        if src_usage == 'supplier' and dest_usage == 'customer':
            pick_purchase = pick.move_lines and pick.move_lines[0].purchase_line_id and pick.move_lines[0].purchase_line_id.order_id.invoice_method == 'picking'
            if pick_purchase:
                return 'in_invoice'
            else:
                return 'out_invoice'
        else:
            return super(StockInvoiceOnshipping, self)._get_invoice_type()

    def _default_second_journal_id(self):
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
    def _compute_wizard_title(self):
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
                                        default=_default_second_journal_id)
    wizard_title = fields.Char('Wizard Title', compute='_compute_wizard_title', readonly=True)
