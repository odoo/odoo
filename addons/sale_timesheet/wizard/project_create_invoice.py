# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ProjectCreateInvoice(models.TransientModel):
    _name = 'project.create.invoice'
    _description = "Create Invoice from project"

    @api.model
    def default_get(self, fields):
        result = super().default_get(fields)

        active_model = self._context.get('active_model')
        if active_model != 'project.project':
            raise UserError(_('You can only apply this action from a project.'))

        active_id = self._context.get('active_id')
        if 'project_id' in fields and active_id:
            result['project_id'] = active_id
        return result

    project_id = fields.Many2one('project.project', "Project", help="Project to make billable", required=True)
    _candidate_orders = fields.Many2many('sale.order', compute='_compute_candidate_orders', export_string_translation=False)
    sale_order_id = fields.Many2one(
        'sale.order', string="Choose the Sales Order to invoice", required=True,
        domain="[('id', 'in', _candidate_orders)]"
    )
    amount_to_invoice = fields.Monetary("Amount to invoice", compute='_compute_amount_to_invoice', currency_field='currency_id', help="Total amount to invoice on the sales order, including all items (services, storables, expenses, ...)")
    currency_id = fields.Many2one(related='sale_order_id.currency_id', readonly=True, export_string_translation=False)

    @api.depends('project_id.tasks.sale_line_id.order_id.invoice_status')
    def _compute_candidate_orders(self):
        for p in self:
            p._candidate_orders = p.project_id\
                .tasks.sale_line_id.order_id\
                .filtered(lambda so: so.invoice_status == 'to invoice')

    @api.depends('sale_order_id')
    def _compute_amount_to_invoice(self):
        for wizard in self:
            amount_untaxed = 0.0
            amount_tax = 0.0
            for line in wizard.sale_order_id.order_line.filtered(lambda sol: sol.invoice_status == 'to invoice'):
                amount_untaxed += line.price_reduce * line.qty_to_invoice
                amount_tax += line.price_tax
            wizard.amount_to_invoice = amount_untaxed + amount_tax

    def action_create_invoice(self):
        if not self.sale_order_id and self.sale_order_id.invoice_status != 'to invoice':
            raise UserError(_("The selected Sales Order should contain something to invoice."))
        action = self.env["ir.actions.actions"]._for_xml_id("sale.action_view_sale_advance_payment_inv")
        action['context'] = {
            'active_ids': self.sale_order_id.ids
        }
        return action
