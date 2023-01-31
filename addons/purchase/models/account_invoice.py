# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class AccountMove(models.Model):
    _inherit = 'account.move'

    purchase_vendor_bill_id = fields.Many2one('purchase.bill.union', store=False, readonly=True,
        states={'draft': [('readonly', False)]},
        string='Auto-complete',
        help="Auto-complete from a past bill / purchase order.")
    purchase_id = fields.Many2one('purchase.order', store=False, readonly=True,
        states={'draft': [('readonly', False)]},
        string='Purchase Order',
        help="Auto-complete from a past purchase order.")

    def _get_invoice_reference(self):
        self.ensure_one()
        vendor_refs = [ref for ref in set(self.line_ids.mapped('purchase_line_id.order_id.partner_ref')) if ref]
        if self.ref:
            return [ref for ref in self.ref.split(', ') if ref and ref not in vendor_refs] + vendor_refs
        return vendor_refs

    @api.onchange('purchase_vendor_bill_id', 'purchase_id')
    def _onchange_purchase_auto_complete(self):
        ''' Load from either an old purchase order, either an old vendor bill.

        When setting a 'purchase.bill.union' in 'purchase_vendor_bill_id':
        * If it's a vendor bill, 'invoice_vendor_bill_id' is set and the loading is done by '_onchange_invoice_vendor_bill'.
        * If it's a purchase order, 'purchase_id' is set and this method will load lines.

        /!\ All this not-stored fields must be empty at the end of this function.
        '''
        if self.purchase_vendor_bill_id.vendor_bill_id:
            self.invoice_vendor_bill_id = self.purchase_vendor_bill_id.vendor_bill_id
            self._onchange_invoice_vendor_bill()
        elif self.purchase_vendor_bill_id.purchase_order_id:
            self.purchase_id = self.purchase_vendor_bill_id.purchase_order_id
        self.purchase_vendor_bill_id = False

        if not self.purchase_id:
            return

        # Copy data from PO
        invoice_vals = self.purchase_id.with_company(self.purchase_id.company_id)._prepare_invoice()
        invoice_vals['currency_id'] = self.line_ids and self.currency_id or invoice_vals.get('currency_id')
        del invoice_vals['ref']
        self.update(invoice_vals)

        # Copy purchase lines.
        po_lines = self.purchase_id.order_line - self.line_ids.mapped('purchase_line_id')
        new_lines = self.env['account.move.line']
        sequence = max(self.line_ids.mapped('sequence')) + 1 if self.line_ids else 10
        for line in po_lines.filtered(lambda l: not l.display_type):
            line_vals = line._prepare_account_move_line(self)
            line_vals.update({'sequence': sequence})
            new_line = new_lines.new(line_vals)
            sequence += 1
            new_line.account_id = new_line._get_computed_account()
            new_line._onchange_price_subtotal()
            new_lines += new_line
        new_lines._onchange_mark_recompute_taxes()

        # Compute invoice_origin.
        origins = set(self.line_ids.mapped('purchase_line_id.order_id.name'))
        self.invoice_origin = ','.join(list(origins))

        # Compute ref.
        refs = self._get_invoice_reference()
        self.ref = ', '.join(refs)

        # Compute payment_reference.
        if len(refs) == 1:
            self.payment_reference = refs[0]

        self.purchase_id = False
        self._onchange_currency()

    @api.onchange('partner_id', 'company_id')
    def _onchange_partner_id(self):
        res = super(AccountMove, self)._onchange_partner_id()
        if self.partner_id and\
                self.move_type in ['in_invoice', 'in_refund'] and\
                self.currency_id != self.partner_id.property_purchase_currency_id and\
                self.partner_id.property_purchase_currency_id.id:
            if not self.env.context.get('default_journal_id'):
                journal_domain = [
                    ('type', '=', 'purchase'),
                    ('company_id', '=', self.company_id.id),
                    ('currency_id', '=', self.partner_id.property_purchase_currency_id.id),
                ]
                default_journal_id = self.env['account.journal'].search(journal_domain, limit=1)
                if default_journal_id:
                    self.journal_id = default_journal_id
            if self.env.context.get('default_currency_id'):
                self.currency_id = self.env.context['default_currency_id']
            if self.partner_id.property_purchase_currency_id:
                self.currency_id = self.partner_id.property_purchase_currency_id
        return res

    @api.model_create_multi
    def create(self, vals_list):
        # OVERRIDE
        moves = super(AccountMove, self).create(vals_list)
        for move in moves:
            if move.reversed_entry_id:
                continue
            purchase = move.line_ids.mapped('purchase_line_id.order_id')
            if not purchase:
                continue
            refs = ["<a href=# data-oe-model=purchase.order data-oe-id=%s>%s</a>" % tuple(name_get) for name_get in purchase.name_get()]
            message = _("This vendor bill has been created from: %s") % ','.join(refs)
            move.message_post(body=message)
        return moves

    def write(self, vals):
        # OVERRIDE
        old_purchases = [move.mapped('line_ids.purchase_line_id.order_id') for move in self]
        res = super(AccountMove, self).write(vals)
        for i, move in enumerate(self):
            new_purchases = move.mapped('line_ids.purchase_line_id.order_id')
            if not new_purchases:
                continue
            diff_purchases = new_purchases - old_purchases[i]
            if diff_purchases:
                refs = ["<a href=# data-oe-model=purchase.order data-oe-id=%s>%s</a>" % tuple(name_get) for name_get in diff_purchases.name_get()]
                message = _("This vendor bill has been modified from: %s") % ','.join(refs)
                move.message_post(body=message)
        return res


class AccountMoveLine(models.Model):
    """ Override AccountInvoice_line to add the link to the purchase order line it is related to"""
    _inherit = 'account.move.line'

    purchase_line_id = fields.Many2one('purchase.order.line', 'Purchase Order Line', ondelete='set null', index=True)
    purchase_order_id = fields.Many2one('purchase.order', 'Purchase Order', related='purchase_line_id.order_id', readonly=True)

    def _copy_data_extend_business_fields(self, values):
        # OVERRIDE to copy the 'purchase_line_id' field as well.
        super(AccountMoveLine, self)._copy_data_extend_business_fields(values)
        values['purchase_line_id'] = self.purchase_line_id.id
