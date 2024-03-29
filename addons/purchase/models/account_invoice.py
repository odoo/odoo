# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import difflib
import logging
import time
from markupsafe import Markup

from odoo import api, fields, models, Command, _

_logger = logging.getLogger(__name__)

TOLERANCE = 0.02  # tolerance applied to the total when searching for a matching purchase order


class AccountMove(models.Model):
    _inherit = 'account.move'

    purchase_vendor_bill_id = fields.Many2one('purchase.bill.union', store=False, readonly=False,
        string='Auto-complete',
        help="Auto-complete from a past bill / purchase order.")
    purchase_id = fields.Many2one('purchase.order', store=False, readonly=False,
        string='Purchase Order',
        help="Auto-complete from a past purchase order.")
    purchase_order_count = fields.Integer(compute="_compute_origin_po_count", string='Purchase Order Count')

    def _get_invoice_reference(self):
        self.ensure_one()
        vendor_refs = [ref for ref in set(self.invoice_line_ids.mapped('purchase_line_id.order_id.partner_ref')) if ref]
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
        new_currency_id = self.invoice_line_ids and self.currency_id or invoice_vals.get('currency_id')
        del invoice_vals['ref'], invoice_vals['payment_reference']
        del invoice_vals['company_id']  # avoid recomputing the currency
        if self.move_type == invoice_vals['move_type']:
            del invoice_vals['move_type'] # no need to be updated if it's same value, to avoid recomputes
        self.update(invoice_vals)
        self.currency_id = new_currency_id

        # Copy purchase lines.
        po_lines = self.purchase_id.order_line - self.invoice_line_ids.mapped('purchase_line_id')
        for line in po_lines.filtered(lambda l: not l.display_type):
            self.invoice_line_ids += self.env['account.move.line'].new(
                line._prepare_account_move_line(self)
            )

        # Compute invoice_origin.
        origins = set(self.invoice_line_ids.mapped('purchase_line_id.order_id.name'))
        self.invoice_origin = ','.join(list(origins))

        # Compute ref.
        refs = self._get_invoice_reference()
        self.ref = ', '.join(refs)

        # Compute payment_reference.
        if not self.payment_reference:
            if len(refs) == 1:
                self.payment_reference = refs[0]
            elif len(refs) > 1:
                self.payment_reference = refs[-1]

        self.purchase_id = False

    @api.onchange('partner_id', 'company_id')
    def _onchange_partner_id(self):
        res = super(AccountMove, self)._onchange_partner_id()

        currency_id = (
                self.partner_id.property_purchase_currency_id
                or self.env['res.currency'].browse(self.env.context.get("default_currency_id"))
                or self.currency_id
        )

        if self.partner_id and self.move_type in ['in_invoice', 'in_refund'] and self.currency_id != currency_id:
            if not self.env.context.get('default_journal_id'):
                journal_domain = [
                    *self.env['account.journal']._check_company_domain(self.company_id),
                    ('type', '=', 'purchase'),
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
            message = _("This vendor bill has been created from: ") + Markup(',').join(refs)
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
                message = _("This vendor bill has been modified from: ") + Markup(',').join(refs)
                move.message_post(body=message)
        return res

    def _find_matching_subset_po_lines(self, po_lines_with_amount, goal_total, timeout):
        """Finds the purchase order lines adding up to the goal amount.

        The problem of finding the subset of `po_lines_with_amount` which sums up to `goal_total` reduces to
        the 0-1 Knapsack problem. The dynamic programming approach to solve this problem is most of the time slower
        than this because identical sub-problems don't arise often enough. It returns the list of purchase order lines
        which sum up to `goal_total` or an empty list if multiple or no solutions were found.

        :param po_lines_with_amount: a dict (str: float|recordset) containing:
            * line: an `purchase.order.line`
            * amount_to_invoice: the remaining amount to be invoiced of the line
        :param goal_total: the total amount to match with a subset of purchase order lines
        :param timeout: the max time the line matching algorithm can take before timing out
        :return: list of `purchase.order.line` whose remaining sum matches `goal_total`
        """
        def find_matching_subset_po_lines(lines, goal):
            if time.time() - start_time > timeout:
                raise TimeoutError
            solutions = []
            for i, line in enumerate(lines):
                if line['amount_to_invoice'] < goal - TOLERANCE:
                    # The amount to invoice of the current purchase order line is less than the amount we still need on
                    # the vendor bill.
                    # We try finding purchase order lines that match the remaining vendor bill amount minus the amount
                    # to invoice of the current purchase order line. We only look in the purchase order lines that we
                    # haven't passed yet.
                    sub_solutions = find_matching_subset_po_lines(lines[i + 1:], goal - line['amount_to_invoice'])
                    # We add all possible sub-solutions' purchase order lines in a tuple together with our current
                    # purchase order line.
                    solutions.extend((line['line'], *solution) for solution in sub_solutions)
                elif goal - TOLERANCE <= line['amount_to_invoice'] <= goal + TOLERANCE:
                    # The amount to invoice of the current purchase order line matches the remaining vendor bill amount.
                    # We add this purchase order line to our list of solutions.
                    solutions.append([line['line']])
                if len(solutions) > 1:
                    # More than one solution was found. We can't know for sure which is the correct one, so we don't
                    # return any solution.
                    return []
            return solutions
        start_time = time.time()
        try:
            subsets = find_matching_subset_po_lines(
                sorted(po_lines_with_amount, key=lambda line: line['amount_to_invoice'], reverse=True),
                goal_total
            )
            return subsets[0] if subsets else []
        except TimeoutError:
            _logger.warning("Timed out during search of a matching subset of purchase order lines")
            return []

    def _find_matching_po_and_inv_lines(self, po_lines, inv_lines, timeout):
        """Finds purchase order lines that match some of the invoice lines.

        We try to find a purchase order line for every invoice line matching on the unit price and having at least
        the same quantity to invoice.

        :param po_lines: list of purchase order lines that can be matched
        :param inv_lines: list of invoice lines to be matched
        :param timeout: how long this function can run before we consider it too long
        :return: a tuple (list, list) containing:
            * matched 'purchase.order.line'
            * tuple of purchase order line ids and their matched 'account.move.line'
        """
        # Sort the invoice lines by unit price and quantity to speed up matching
        invoice_lines = sorted(inv_lines, key=lambda line: (line.price_unit, line.quantity), reverse=True)
        # Sort the purchase order lines by unit price and remaining quantity to speed up matching
        purchase_lines = sorted(
            po_lines,
            key=lambda line: (line.price_unit, line.product_qty - line.qty_invoiced),
            reverse=True
        )
        matched_po_lines = []
        matched_inv_lines = []
        try:
            start_time = time.time()
            for invoice_line in invoice_lines:
                # There are no purchase order lines left. We are done matching.
                if not purchase_lines:
                    break
                # A dict of purchase lines mapping to a diff score for the name
                purchase_line_candidates = {}
                for purchase_line in purchase_lines:
                    if time.time() - start_time > timeout:
                        raise TimeoutError

                    # The lists are sorted by unit price descendingly.
                    # When the unit price of the purchase line is lower than the unit price of the invoice line,
                    # we cannot get a match anymore.
                    if purchase_line.price_unit < invoice_line.price_unit:
                        break

                    if (invoice_line.price_unit == purchase_line.price_unit
                            and invoice_line.quantity <= purchase_line.product_qty - purchase_line.qty_invoiced):
                        # The current purchase line is a possible match for the current invoice line.
                        # We calculate the name match ratio and continue with other possible matches.
                        #
                        # We could match on more fields coming from an EDI invoice, but that requires extending the
                        # account.move.line model with the extra matching fields and extending the EDI extraction
                        # logic to fill these new fields.
                        purchase_line_candidates[purchase_line] = difflib.SequenceMatcher(
                            None, invoice_line.name, purchase_line.name).ratio()

                if len(purchase_line_candidates) > 0:
                    # We take the best match based on the name.
                    purchase_line_match = max(purchase_line_candidates, key=purchase_line_candidates.get)
                    if purchase_line_match:
                        # We found a match. We remove the purchase order line so it does not get matched twice.
                        purchase_lines.remove(purchase_line_match)
                        matched_po_lines.append(purchase_line_match)
                        matched_inv_lines.append((purchase_line_match.id, invoice_line))

            return (matched_po_lines, matched_inv_lines)

        except TimeoutError:
            _logger.warning('Timed out during search of matching purchase order lines')
            return ([], [])

    def _set_purchase_orders(self, purchase_orders, force_write=True):
        """Link the given purchase orders to this vendor bill and add their lines as invoice lines.

        :param purchase_orders: a list of purchase orders to be linked to this vendor bill
        :param force_write: whether to delete all existing invoice lines before adding the vendor bill lines
        """
        with self.env.cr.savepoint():
            with self._get_edi_creation() as invoice:
                if force_write and invoice.line_ids:
                    invoice.invoice_line_ids = [Command.clear()]
                for purchase_order in purchase_orders:
                    invoice.invoice_line_ids = [Command.create({
                        'display_type': 'line_section',
                        'name': _('From %s', purchase_order.name)
                    })]
                    invoice.purchase_id = purchase_order
                    invoice._onchange_purchase_auto_complete()

    def _match_purchase_orders(self, po_references, partner_id, amount_total, from_ocr, timeout):
        """Tries to match open purchase order lines with this invoice given the information we have.

        :param po_references: a list of potential purchase order references/names
        :param partner_id: the vendor id inferred from the vendor bill
        :param amount_total: the total amount of the vendor bill
        :param from_ocr: indicates whether this vendor bill was created from an OCR scan (less reliable)
        :param timeout: the max time the line matching algorithm can take before timing out
        :return: tuple (str, recordset, dict) containing:
            * the match method:
                * `total_match`: purchase order reference(s) and total amounts match perfectly
                * `subset_total_match`: a subset of the referenced purchase orders' lines matches the total amount of
                    this invoice (OCR only)
                * `po_match`: only the purchase order reference matches (OCR only)
                * `subset_match`: a subset of the referenced purchase orders' lines matches a subset of the invoice
                    lines based on unit prices (EDI only)
                * `no_match`: no result found
            * recordset of `purchase.order.line` containing purchase order lines matched with an invoice line
            * list of tuple containing every `purchase.order.line` id and its related `account.move.line`
        """

        common_domain = [
            ('company_id', '=', self.company_id.id),
            ('state', '=', 'purchase'),
            ('invoice_status', 'in', ('to invoice', 'no'))
        ]

        matching_purchase_orders = self.env['purchase.order']

        # We have purchase order references in our vendor bill and a total amount.
        if po_references and amount_total:
            # We first try looking for purchase orders whose names match one of the purchase order references in the
            # vendor bill.
            matching_purchase_orders |= self.env['purchase.order'].search(
                common_domain + [('name', 'in', po_references)])

            if not matching_purchase_orders:
                # If not found, we try looking for purchase orders whose `partner_ref` field matches one of the
                # purchase order references in the vendor bill.
                matching_purchase_orders |= self.env['purchase.order'].search(
                    common_domain + [('partner_ref', 'in', po_references)])

            if matching_purchase_orders:
                # We found matching purchase orders and are extracting all purchase order lines together with their
                # amounts still to be invoiced.
                po_lines = [line for line in matching_purchase_orders.order_line if line.product_qty]
                po_lines_with_amount = [{
                    'line': line,
                    'amount_to_invoice': (1 - line.qty_invoiced / line.product_qty) * line.price_total,
                } for line in po_lines]

                # If the sum of all remaining amounts to be invoiced for these purchase orders' lines is within a
                # tolerance from the vendor bill total, we have a total match. We return all purchase order lines
                # summing up to this vendor bill's total (could be from multiple purchase orders).
                if (amount_total - TOLERANCE
                        < sum(line['amount_to_invoice'] for line in po_lines_with_amount)
                        < amount_total + TOLERANCE):
                    return 'total_match', matching_purchase_orders.order_line, None

                elif from_ocr:
                    # The invoice comes from an OCR scan.
                    # We try to match the invoice total with purchase order lines.
                    matching_po_lines = self._find_matching_subset_po_lines(
                        po_lines_with_amount, amount_total, timeout)
                    if matching_po_lines:
                        return 'subset_total_match', self.env['purchase.order.line'].union(*matching_po_lines), None
                    else:
                        # We did not find a match for the invoice total.
                        # We return all purchase order lines based only on the purchase order reference(s) in the
                        # vendor bill.
                        return 'po_match', matching_purchase_orders.order_line, None

                else:
                    # We have an invoice from an EDI document, so we try to match individual invoice lines with
                    # individual purchase order lines from referenced purchase orders.
                    matching_po_lines, matching_inv_lines = self._find_matching_po_and_inv_lines(
                        po_lines, self.line_ids, timeout)

                    if matching_po_lines:
                        # We found a subset of purchase order lines that match a subset of the vendor bill lines.
                        # We return the matching purchase order lines and vendor bill lines.
                        return ('subset_match',
                                self.env['purchase.order.line'].union(*matching_po_lines),
                                matching_inv_lines)

        # As a last resort we try matching a purchase order by vendor and total amount.
        if partner_id and amount_total:
            purchase_id_domain = common_domain + [
                ('partner_id', 'child_of', [partner_id]),
                ('amount_total', '>=', amount_total - TOLERANCE),
                ('amount_total', '<=', amount_total + TOLERANCE)
            ]
            matching_purchase_orders = self.env['purchase.order'].search(purchase_id_domain)
            if len(matching_purchase_orders) == 1:
                # We found exactly one match on vendor and total amount (within tolerance).
                # We return all purchase order lines of the purchase order whose total amount matched our vendor bill.
                return 'total_match', matching_purchase_orders.order_line, None

        # We couldn't find anything, so we return no lines.
        return ('no_match', matching_purchase_orders.order_line, None)

    def _find_and_set_purchase_orders(self, po_references, partner_id, amount_total, from_ocr=False, timeout=10):
        """Finds related purchase orders that (partially) match the vendor bill and links the matching lines on this
        vendor bill.

        :param po_references: a list of potential purchase order references/names
        :param partner_id: the vendor id matched on the vendor bill
        :param amount_total: the total amount of the vendor bill
        :param from_ocr: indicates whether this vendor bill was created from an OCR scan (less reliable)
        :param timeout: the max time the line matching algorithm can take before timing out
        """
        self.ensure_one()

        method, matched_po_lines, matched_inv_lines = self._match_purchase_orders(
            po_references, partner_id, amount_total, from_ocr, timeout
        )

        if method in ('total_match', 'po_match'):
            # The purchase order reference(s) and total amounts match perfectly or there is only one purchase order
            # reference that matches with an OCR invoice. We replace the invoice lines with the purchase order lines.
            self._set_purchase_orders(matched_po_lines.order_id, force_write=True)

        elif method == 'subset_total_match':
            # A subset of the referenced purchase order lines matches the total amount of this invoice.
            # We keep the invoice lines, but add all the lines from the partially matched purchase orders:
            #   * "naively" matched purchase order lines keep their quantity
            #   * unmatched purchase order lines are added with their quantity set to 0
            self._set_purchase_orders(matched_po_lines.order_id, force_write=False)

            with self._get_edi_creation() as invoice:
                unmatched_lines = invoice.invoice_line_ids.filtered(
                    lambda l: l.purchase_line_id and l.purchase_line_id not in matched_po_lines)
                invoice.invoice_line_ids = [Command.update(line.id, {'quantity': 0}) for line in unmatched_lines]

        elif method == 'subset_match':
            # A subset of the referenced purchase order lines matches a subset of the invoice lines.
            # We add the purchase order lines, but adjust the quantity to the quantities in the invoice.
            # The original invoice lines that correspond with a purchase order line are removed.
            self._set_purchase_orders(matched_po_lines.order_id, force_write=False)

            with self._get_edi_creation() as invoice:
                unmatched_lines = invoice.invoice_line_ids.filtered(
                    lambda l: l.purchase_line_id and l.purchase_line_id not in matched_po_lines)
                invoice.invoice_line_ids = [Command.delete(line.id) for line in unmatched_lines]

                # We remove the original matched invoice lines and apply their quantities and taxes to the matched
                # purchase order lines.
                inv_and_po_lines = list(map(lambda line: (
                        invoice.invoice_line_ids.filtered(
                            lambda l: l.purchase_line_id and l.purchase_line_id.id == line[0]),
                        invoice.invoice_line_ids.filtered(
                            lambda l: l in line[1])
                    ),
                    matched_inv_lines
                ))
                invoice.invoice_line_ids = [
                    Command.update(po_line.id, {'quantity': inv_line.quantity, 'tax_ids': inv_line.tax_ids})
                    for po_line, inv_line in inv_and_po_lines
                ]
                invoice.invoice_line_ids = [Command.delete(inv_line.id) for dummy, inv_line in inv_and_po_lines]

                # If there are lines left not linked to a purchase order, we add a header
                unmatched_lines = invoice.invoice_line_ids.filtered(lambda l: not l.purchase_line_id)
                if len(unmatched_lines) > 0:
                    invoice.invoice_line_ids = [Command.create({
                        'display_type': 'line_section',
                        'name': _('From Electronic Document'),
                        'sequence': -1,
                    })]



class AccountMoveLine(models.Model):
    """ Override AccountInvoice_line to add the link to the purchase order line it is related to"""
    _inherit = 'account.move.line'

    purchase_line_id = fields.Many2one('purchase.order.line', 'Purchase Order Line', ondelete='set null', index='btree_not_null')
    purchase_order_id = fields.Many2one('purchase.order', 'Purchase Order', related='purchase_line_id.order_id', readonly=True)

    def _copy_data_extend_business_fields(self, values):
        # OVERRIDE to copy the 'purchase_line_id' field as well.
        super(AccountMoveLine, self)._copy_data_extend_business_fields(values)
        values['purchase_line_id'] = self.purchase_line_id.id
