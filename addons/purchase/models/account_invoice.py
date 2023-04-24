# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import time

from odoo import api, fields, models, Command, _

_logger = logging.getLogger(__name__)

TOLERANCE = 0.02  # tolerance applied to the total when searching for a matching purchase order


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
    purchase_order_count = fields.Integer(compute="_compute_origin_po_count", string='Purchase Order Count')

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
        invoice_vals['currency_id'] = self.invoice_line_ids and self.currency_id or invoice_vals.get('currency_id')
        del invoice_vals['ref']
        del invoice_vals['company_id']  # avoid recomputing the currency
        self.update(invoice_vals)

        # Copy purchase lines.
        po_lines = self.purchase_id.order_line - self.invoice_line_ids.mapped('purchase_line_id')
        for line in po_lines.filtered(lambda l: not l.display_type):
            self.invoice_line_ids += self.env['account.move.line'].new(
                line._prepare_account_move_line(self)
            )

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

    @api.onchange('partner_id', 'company_id')
    def _onchange_partner_id(self):
        res = super(AccountMove, self)._onchange_partner_id()

        currency_id = (
                self.partner_id.property_purchase_currency_id
                or self.env.context.get("default_currency_id")
                or self.currency_id
        )

        if self.partner_id and self.move_type in ['in_invoice', 'in_refund'] and self.currency_id != currency_id:
            if not self.env.context.get('default_journal_id'):
                journal_domain = [
                    ('type', '=', 'purchase'),
                    ('company_id', '=', self.company_id.id),
                    ('currency_id', '=', currency_id.id),
                ]
                default_journal_id = self.env['account.journal'].search(journal_domain, limit=1)
                if default_journal_id:
                    self.journal_id = default_journal_id

            self.currency_id = currency_id

        return res

    @api.depends('line_ids.purchase_line_id')
    def _compute_origin_po_count(self):
        for move in self:
            move.purchase_order_count = len(move.line_ids.purchase_line_id.order_id)

    def action_view_source_purchase_orders(self):
        self.ensure_one()
        source_orders = self.line_ids.purchase_line_id.order_id
        result = self.env['ir.actions.act_window']._for_xml_id('purchase.purchase_form_action')
        if len(source_orders) > 1:
            result['domain'] = [('id', 'in', source_orders.ids)]
        elif len(source_orders) == 1:
            result['views'] = [(self.env.ref('purchase.purchase_order_form', False).id, 'form')]
            result['res_id'] = source_orders.id
        else:
            result = {'type': 'ir.actions.act_window_close'}
        return result

    @api.model_create_multi
    def create(self, vals_list):
        # OVERRIDE
        moves = super(AccountMove, self).create(vals_list)
        for move in moves:
            if move.reversed_entry_id:
                continue
            purchases = move.line_ids.purchase_line_id.order_id
            if not purchases:
                continue
            refs = [purchase._get_html_link() for purchase in purchases]
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
                refs = [purchase._get_html_link() for purchase in diff_purchases]
                message = _("This vendor bill has been modified from: %s") % ','.join(refs)
                move.message_post(body=message)
        return res

    def find_matching_subset_invoice_lines(self, invoice_lines, goal_total, timeout):
        """ The problem of finding the subset of `invoice_lines` which sums up to `goal_total` reduces to the 0-1 Knapsack problem.
        The dynamic programming approach to solve this problem is most of the time slower than this because identical sub-problems don't arise often enough.
        It returns the list of invoice lines which sums up to `goal_total` or an empty list if multiple or no solutions were found."""
        def _find_matching_subset_invoice_lines(lines, goal):
            if time.time() - start_time > timeout:
                raise TimeoutError
            solutions = []
            for i, line in enumerate(lines):
                if line['amount_to_invoice'] < goal - TOLERANCE:
                    sub_solutions = _find_matching_subset_invoice_lines(lines[i + 1:], goal - line['amount_to_invoice'])
                    solutions.extend((line, *solution) for solution in sub_solutions)
                elif goal - TOLERANCE <= line['amount_to_invoice'] <= goal + TOLERANCE:
                    solutions.append([line])
                if len(solutions) > 1:
                    # More than 1 solution found, we can't know for sure which is the correct one, so we don't return any solution
                    return []
            return solutions
        start_time = time.time()
        try:
            subsets = _find_matching_subset_invoice_lines(sorted(invoice_lines, key=lambda line: line['amount_to_invoice'], reverse=True), goal_total)
            return subsets[0] if subsets else []
        except TimeoutError:
            _logger.warning("Timed out during search of a matching subset of invoice lines")
            return []

    def _set_purchase_orders(self, purchase_orders, force_write=True):
        with self.env.cr.savepoint():
            with self._get_edi_creation() as move_form:
                if force_write and move_form.line_ids:
                    move_form.invoice_line_ids = [Command.clear()]
                for purchase_order in purchase_orders:
                    move_form.invoice_line_ids = [Command.create({
                        'display_type': 'line_section',
                        'name': _('From %s document', purchase_order.name)
                    })]
                    move_form.purchase_id = purchase_order
                    move_form._onchange_purchase_auto_complete()

    def _match_purchase_orders(self, po_references, partner_id, amount_total, timeout):
        """ Tries to match a purchase order given some bill arguments/hints.

        :param po_references: A list of potencial purchase order references/name.
        :param partner_id: The vendor id.
        :param amount_total: The vendor bill total.
        :param timeout: The timeout for subline search
        :return: A tuple containing:
            * a str which is the match method:
                'total_match': the invoice amount AND the partner or bill' reference match
                'subset_total_match': the reference AND a subset of line that match the bill amount total
                'po_match': only the reference match
                'no_match': no result found
            * recordset of matched 'purchase.order.line' (could come from more than one purchase.order)
        """
        common_domain = [('company_id', '=', self.company_id.id), ('state', '=', 'purchase'), ('invoice_status', 'in', ('to invoice', 'no'))]

        matching_pos = self.env['purchase.order']
        if po_references and amount_total:
            matching_pos |= self.env['purchase.order'].search(common_domain + [('name', 'in', po_references)])

            if not matching_pos:
                matching_pos |= self.env['purchase.order'].search(common_domain + [('partner_ref', 'in', po_references)])

            if matching_pos:
                matching_pos_invoice_lines = [{
                    'line': line,
                    'amount_to_invoice': (1 - line.qty_invoiced / line.product_qty) * line.price_total,
                } for line in matching_pos.order_line if line.product_qty]

                if amount_total - TOLERANCE < sum(line['amount_to_invoice'] for line in matching_pos_invoice_lines) < amount_total + TOLERANCE:
                    return 'total_match', matching_pos.order_line

                else:
                    il_subset = self.find_matching_subset_invoice_lines(matching_pos_invoice_lines, amount_total, timeout)
                    if il_subset:
                        return 'subset_total_match', self.env['purchase.order.line'].union(*[line['line'] for line in il_subset])
                    else:
                        return 'po_match', matching_pos.order_line

        if partner_id and amount_total:
            purchase_id_domain = common_domain + [('partner_id', 'child_of', [partner_id]), ('amount_total', '>=', amount_total - TOLERANCE), ('amount_total', '<=', amount_total + TOLERANCE)]
            matching_pos |= self.env['purchase.order'].search(purchase_id_domain)
            if len(matching_pos) == 1:
                return 'total_match', matching_pos.order_line

        return 'no_match', matching_pos.order_line

    def _find_and_set_purchase_orders(self, po_references, partner_id, amount_total, prefer_purchase_line=False, timeout=10):
        self.ensure_one()

        method, matched_po_lines = self._match_purchase_orders(po_references, partner_id, amount_total, timeout)

        if method == 'total_match': # erase all lines and autocomplete
            self._set_purchase_orders(matched_po_lines.order_id, force_write=True)

        elif method == 'subset_total_match': # don't erase and add autocomplete
            self._set_purchase_orders(matched_po_lines.order_id, force_write=False)

            with self._get_edi_creation() as move_form: # logic for unmatched lines
                unmatched_lines = move_form.invoice_line_ids.filtered(
                    lambda l: l.purchase_line_id and l.purchase_line_id not in matched_po_lines)
                for line in unmatched_lines:
                    if prefer_purchase_line:
                        line.quantity = 0
                    else:
                        line.unlink()

                if not prefer_purchase_line:
                    move_form.invoice_line_ids.filtered('purchase_line_id').quantity = 0

        elif method == 'po_match': # erase all lines and autocomplete
            if prefer_purchase_line:
                self._set_purchase_orders(matched_po_lines.order_id, force_write=True)


class AccountMoveLine(models.Model):
    """ Override AccountInvoice_line to add the link to the purchase order line it is related to"""
    _inherit = 'account.move.line'

    purchase_line_id = fields.Many2one('purchase.order.line', 'Purchase Order Line', ondelete='set null', index='btree_not_null')
    purchase_order_id = fields.Many2one('purchase.order', 'Purchase Order', related='purchase_line_id.order_id', readonly=True)

    def _copy_data_extend_business_fields(self, values):
        # OVERRIDE to copy the 'purchase_line_id' field as well.
        super(AccountMoveLine, self)._copy_data_extend_business_fields(values)
        values['purchase_line_id'] = self.purchase_line_id.id
