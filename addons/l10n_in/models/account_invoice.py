# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    @api.depends('amount_total')
    def _compute_amount_total_words(self):
        for invoice in self:
            invoice.amount_total_words = invoice.currency_id.amount_to_text(invoice.amount_total)

    amount_total_words = fields.Char("Total (In Words)", compute="_compute_amount_total_words")
    # Use for invisible fields in form views.
    l10n_in_import_export = fields.Boolean(related='journal_id.l10n_in_import_export', readonly=True)
    # For Export invoice this data is need in GSTR report
    l10n_in_export_type = fields.Selection([
        ('regular', 'Regular'), ('deemed', 'Deemed'),
        ('sale_from_bonded_wh', 'Sale from Bonded WH'),
        ('export_with_igst', 'Export with IGST'),
        ('sez_with_igst', 'SEZ with IGST payment'),
        ('sez_without_igst', 'SEZ without IGST payment')],
        string='Export Type', default='regular', required=True)
    l10n_in_shipping_bill_number = fields.Char('Shipping bill number', readonly=True, states={'draft': [('readonly', False)]})
    l10n_in_shipping_bill_date = fields.Date('Shipping bill date', readonly=True, states={'draft': [('readonly', False)]})
    l10n_in_shipping_port_code_id = fields.Many2one('l10n_in.port.code', 'Shipping port code', states={'draft': [('readonly', False)]})
    l10n_in_reseller_partner_id = fields.Many2one('res.partner', 'Reseller', domain=[('vat', '!=', False)], help="Only Registered Reseller", readonly=True, states={'draft': [('readonly', False)]})
    l10n_in_partner_vat = fields.Char(related="partner_id.vat", readonly=True)

    def _get_report_base_filename(self):
        self.ensure_one()
        if self.company_id.country_id.code != 'IN':
            return super(AccountInvoice, self)._get_report_base_filename()
        return self.type == 'out_invoice' and self.state == 'draft' and _('Draft %s') % (self.journal_id.name) or \
            self.type == 'out_invoice' and self.state in ('open','in_payment','paid') and '%s - %s' % (self.journal_id.name, self.number) or \
            self.type == 'out_refund' and self.state == 'draft' and _('Credit Note') or \
            self.type == 'out_refund' and _('Credit Note - %s') % (self.number) or \
            self.type == 'in_invoice' and self.state == 'draft' and _('Vendor Bill') or \
            self.type == 'in_invoice' and self.state in ('open','in_payment','paid') and _('Vendor Bill - %s') % (self.number) or \
            self.type == 'in_refund' and self.state == 'draft' and _('Vendor Credit Note') or \
            self.type == 'in_refund' and _('Vendor Credit Note - %s') % (self.number)

    @api.multi
    def _invoice_line_tax_values(self):
        self.ensure_one()
        tax_datas = {}
        TAX = self.env['account.tax']
        for line in self.mapped('invoice_line_ids'):
            price_unit = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            tax_lines = line.invoice_line_tax_ids.compute_all(price_unit, line.invoice_id.currency_id, line.quantity, line.product_id, line.invoice_id.partner_id, self.type in ('in_refund', 'out_refund'))['taxes']
            for tax_line in tax_lines:
                tax_line['tag_ids'] = TAX.browse(tax_line['id']).tag_ids.ids
            tax_datas[line.id] = tax_lines
        return tax_datas

    def inv_line_characteristic_hashcode(self, invoice_line):
        res = super(AccountInvoice, self).inv_line_characteristic_hashcode(invoice_line)
        return res + "-%s" %(invoice_line.get('product_uom_id', 'False'))

    @api.model
    def tax_line_move_line_get(self):
        res = super(AccountInvoice, self).tax_line_move_line_get()
        for vals in res:
            invoice_tax_line = self.env['account.invoice.tax'].browse(vals.get('invoice_tax_line_id'))
            vals['product_id'] = invoice_tax_line.l10n_in_product_id.id
            vals['uom_id'] = invoice_tax_line.l10n_in_uom_id.id
            vals['quantity'] = invoice_tax_line.l10n_in_quantity
        return res

    def _prepare_tax_line_vals(self, line, tax, tax_ids):
        vals = super(AccountInvoice, self)._prepare_tax_line_vals(line, tax, tax_ids)
        vals['l10n_in_product_id'] = line.product_id.id
        vals['l10n_in_uom_id'] = line.uom_id.id
        vals['l10n_in_quantity'] = line.quantity
        return vals

    @api.multi
    def get_taxes_values(self, tax_group_fields=False):
        if tax_group_fields:
            tax_group_fields |= set(['l10n_in_quantity'])
        else:
            tax_group_fields = set(['l10n_in_quantity'])
        return super(AccountInvoice, self).get_taxes_values(tax_group_fields)


class AccountInvoiceTax(models.Model):
    _inherit = "account.invoice.tax"

    l10n_in_product_id = fields.Many2one('product.product', string='Product')
    l10n_in_uom_id = fields.Many2one('uom.uom', string='Unit of Measure')
    l10n_in_quantity = fields.Float(string='Quantity')

    @api.multi
    def _prepare_invoice_tax_val(self):
        res = super(AccountInvoiceTax, self)._prepare_invoice_tax_val()
        res['l10n_in_product_id'] = self.l10n_in_product_id.id
        res['l10n_in_uom_id'] = self.l10n_in_uom_id.id
        return res
