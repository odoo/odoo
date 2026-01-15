# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, Command, _
from odoo.exceptions import UserError


class BillToPoWizard(models.TransientModel):
    _name = 'bill.to.po.wizard'
    _description = 'Bill to Purchase Order'

    purchase_order_id = fields.Many2one(comodel_name='purchase.order')
    partner_id = fields.Many2one(comodel_name='res.partner')

    def action_add_to_po(self):
        aml_ids = [abs(record_id) for record_id in self.env.context.get('active_ids') if record_id < 0]
        lines_to_add = self.env['account.move.line'].browse(aml_ids).filtered(lambda l: l.product_id)
        if not lines_to_add:
            raise UserError(_("There are no products to add to the Purchase Order. Are these Down Payments?"))
        line_vals = lines_to_add._prepare_line_values_for_purchase()
        if self.purchase_order_id:
            new_po_lines = self.env['purchase.order.line'].create([{
                **val,
                'order_id': self.purchase_order_id.id,
            } for val in line_vals])
            self.purchase_order_id.order_line += new_po_lines
        else:
            self.purchase_order_id = self.env['purchase.order'].create({
                'partner_id': lines_to_add.partner_id.id,
                'order_line': [Command.create(val) for val in line_vals],
            })
            new_po_lines = self.purchase_order_id.order_line

        self.purchase_order_id.button_confirm()
        for aml, pol in zip(lines_to_add, new_po_lines):
            if aml.product_id == pol.product_id:
                aml.purchase_line_id = pol.id
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_mode': 'form',
            'res_id': self.purchase_order_id.id,
        }

    def action_add_downpayment(self):
        aml_ids = [abs(record_id) for record_id in self.env.context.get('active_ids') if record_id < 0]
        lines_to_convert = self.env['account.move.line'].browse(aml_ids)
        context = {'lang': lines_to_convert.partner_id.lang}
        if not self.purchase_order_id:
            self.purchase_order_id = self.env['purchase.order'].create({
                'partner_id': lines_to_convert.partner_id.id,
            })
        po_currency = self.purchase_order_id.currency_id
        company = self.purchase_order_id.company_id
        date = self.purchase_order_id.date_order or fields.Date.today()
        line_vals = [
            {
                'name': _("Down Payment (ref: %(ref)s)", ref=aml.display_name),
                'product_qty': 0.0,
                'product_uom_id': aml.product_uom_id.id,
                'is_downpayment': True,
                'price_unit': aml.currency_id._convert(aml.price_unit, po_currency, company, date) if aml.currency_id != po_currency else aml.price_unit,
                'tax_ids': aml.tax_ids,
                'order_id': self.purchase_order_id.id,
            }
            for aml in lines_to_convert
        ]
        del context

        downpayment_lines = self.purchase_order_id._create_downpayments(line_vals)
        for aml, dpl in zip(lines_to_convert, downpayment_lines):
            aml.purchase_line_id = dpl.id

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_mode': 'form',
            'res_id': self.purchase_order_id.id,
        }
