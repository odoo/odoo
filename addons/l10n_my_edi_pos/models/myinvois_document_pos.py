# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re

from odoo import api, fields, models

# pos_reference looks like "{year}{device_identifier}-{config_id}-{number}" (see pos.config._get_next_order_refs).
POS_REFERENCE_RE = re.compile(r'^(?P<device>.+)-\d+-(?P<number>\d+)$')


class MyInvoisDocumentPoS(models.Model):
    """
    Odoo's support for consolidated invoice is limited to PoS transactions (for now).
    For regular journal entries, they can easily be sent in batch to MyInvois without the need to group them into
    consolidated invoices.

    These consolidated invoices will be linked to PoS orders, with the purpose of sending them at once each
    month during the allowed timeframe.
    An order that has been invoiced separately must not be included in consolidated invoices.

    A single invoice line could represent multiple transactions as long as their numbering is continuous.

    Note that while the xml generation will be using custom python code, the template will be the same as for regular invoices.
    The API endpoints used will also be the same.
    """
    _inherit = 'myinvois.document'

    # ------------------
    # Fields declaration
    # ------------------

    pos_order_ids = fields.Many2many(
        name="Orders",
        comodel_name="pos.order",
        relation="myinvois_document_pos_order_rel",
        column1="document_id",
        column2="order_id",
        check_company=True,
    )
    pos_config_id = fields.Many2one(
        string="PoS Config",
        comodel_name="pos.config",
        readonly=True,
    )
    linked_order_count = fields.Integer(
        compute='_compute_linked_order_count',
    )
    pos_order_date_range = fields.Char(
        string="Date Range",
        compute='_compute_pos_order_date_range',
        store=True,
    )

    # --------------------------------
    # Compute, inverse, search methods
    # --------------------------------

    def _compute_linked_order_count(self):
        for consolidated_invoice in self:
            consolidated_invoice.linked_order_count = len(consolidated_invoice.pos_order_ids)

    @api.depends('pos_order_ids')
    def _compute_pos_order_date_range(self):
        for consolidated_invoice in self.filtered('pos_order_ids'):
            first_order = consolidated_invoice.pos_order_ids[-1]
            latest_order = consolidated_invoice.pos_order_ids[0]
            consolidated_invoice.pos_order_date_range = f"{first_order.date_order.date()} to {latest_order.date_order.date()}"

    # --------------
    # Action methods
    # --------------

    def action_view_linked_orders(self):
        """ Return the action used to open the order(s) linked to the selected consolidated invoice. """
        self.ensure_one()
        if self.linked_order_count == 1:
            action_vals = {
                'type': 'ir.actions.act_window',
                'res_model': 'pos.order',
                'view_mode': 'form',
                'res_id': self.pos_order_ids.id,
                'views': [(False, 'form')],
            }
        else:
            action_vals = {
                'name': self.env._("Point of Sale Orders"),
                'type': 'ir.actions.act_window',
                'res_model': 'pos.order',
                'view_mode': 'list,form',
                # A dedicated list view is used so that the orders are listed in the order in which they are
                # reported on the consolidated invoice, rather than in the default reverse chronological one.
                'views': [(self.env.ref('l10n_my_edi_pos.view_pos_order_tree_consolidated').id, 'list'), (False, 'form')],
                'domain': [('id', 'in', self.pos_order_ids.ids)],
            }

        return action_vals

    def action_show_myinvois_documents(self):
        """
        Open the documents in self in the correct view based on the amount of records.
        When the documents are linked to pos orders, we use a specific view for them.
        """
        # We'll only use that specific view if all orders are from PoS, in practice they should never be mixed.
        are_pos_document = all(document.pos_order_ids for document in self)
        if not are_pos_document:
            return super().action_show_myinvois_documents()

        if len(self) == 1:
            action_vals = {
                'type': 'ir.actions.act_window',
                'res_model': 'myinvois.document',
                'view_mode': 'form',
                'res_id': self.id,
                'views': [(self.env.ref('l10n_my_edi_pos.myinvois_document_pos_form_view').id, 'form')],
            }
        else:
            action_vals = {
                'name': self.env._("Consolidated Invoices"),
                'type': 'ir.actions.act_window',
                'res_model': 'myinvois.document',
                'view_mode': 'list,form',
                'views': [(self.env.ref('l10n_my_edi_pos.myinvois_document_pos_list_view').id, 'list'), (self.env.ref('l10n_my_edi_pos.myinvois_document_pos_form_view').id, 'form')],
                'domain': [('id', 'in', self.ids)],
            }
        return action_vals

    # ----------------
    # Business methods
    # ----------------

    def _validate_taxes(self):
        """ Makes use of account.edi.xml.ubl_myinvois_my to validate the taxes for the records in self."""
        super()._validate_taxes()
        if self.pos_order_ids:
            self.env["account.edi.xml.ubl_myinvois_my"]._validate_taxes(self.pos_order_ids.lines.tax_ids)

    def _is_consolidated_invoice(self):
        """
        Extend the logic in order to also return true if the document is linked to multiple PoS orders,
        or is a refund of a consolidated invoice generated from the PoS

        :return: True if this invoice is a consolidated invoice or the refund of one.
        """
        self.ensure_one()
        # Note that all documents linked to a PoS order are consolidated invoices, even it there is
        # only one order.
        return super()._is_consolidated_invoice() or self.pos_order_ids

    def _is_consolidated_invoice_refund(self):
        """
        :return: True if this document is a refund specifically for a consolidated invoice from the PoS.
        """
        is_consolidated_invoice_refund = super()._is_consolidated_invoice_refund()
        # Additionally to the existing check in super(), we want to catch refunds for orders linked to PoS orders.
        if self._is_refund_document() and self.invoice_ids.pos_order_ids:
            refunded_order = self.invoice_ids.pos_order_ids[0].refunded_order_id
            is_consolidated_invoice_refund = bool(refunded_order and refunded_order._get_active_consolidated_invoice())
        return is_consolidated_invoice_refund

    def _split_consolidated_invoice_record_in_lines(self):
        """
        :return: A list of pos_order record sets, with one record set representing what would go in one line in the xml.
        """
        if not self._is_consolidated_invoice() or not self.pos_order_ids:
            return super()._split_consolidated_invoice_record_in_lines()
        lines_per_configs = self._split_pos_orders_in_lines(self.pos_order_ids)
        # We create separate documents per config, so at this point _split_pos_orders_in_lines will always return a single config
        return next(iter(lines_per_configs.values()))

    @api.model
    def _split_pos_orders_in_lines(self, pos_order_ids):
        """
        Separate the orders in self into lines as represented in a consolidated invoice, taking care of splitting when
        needed.

        There is no requirement asking to split per sequence (and thus config), but we still do so to make it easier to
        submit per PoS if wanted.

        Two orders are only reported on the same line when they are continuous on all of the following:
        - `sequence_number`, a gapless counter local to a single config, assigned when the order reaches the database.
          A gap means that an order in between was left out of the batch, invoiced separately for example.
        - Their receipt reference: same device, and the receipt number incrementing by one. That number is a counter
          local to a single device, so two orders taken on different devices can carry adjacent numbers without being
          consecutive receipts.
        - Being of the same kind, a receipt made exclusively of refund lines never sharing a line with the sales it
          follows, so that neither is hidden inside the total of the other.
        Requiring all three keeps every line readable as a plain "first-last" range of comparable receipts.

        The two counters not being held at the same level, several devices selling under one config split lines that
        a single device would have kept together: the receipt of another device sitting in between leaves a gap in
        `sequence_number` between two receipts that do follow each other on their own. We accept these extra lines,
        `sequence_number` being the only one of the two counters the server assigns itself - `pos_reference` is
        written by the device, numbering from its own storage and handing the numbers of deleted orders back out
        later, so it cannot vouch on its own that nothing was left out of the batch.

        :param pos_order_ids: The orders to separate.
        :return: A dict of pos order per config, for each config having a list of recordset each representing a single line in the xml.
        """
        lines_per_config = {}
        # We don't mix orders from different configs in a single line as they have different sequences.
        # `_order` being reverse chronological, sorting in reverse yields the oldest orders first, so that the
        # consolidated invoices follow the order they were sold in.
        for config, orders in pos_order_ids.sorted(reverse=True).grouped('config_id').items():
            config_line_ids = []
            previous_order = self.env['pos.order']
            previous_reference = None
            previous_is_refund = False
            for order in orders.sorted('sequence_number'):
                reference = POS_REFERENCE_RE.match(order.pos_reference or '')
                # An order mixing refund lines with new sales is a receipt in its own right, reported like any
                # other with the amounts it refunded already deducted from it.
                is_refund = bool(order.lines) and all(line.refunded_orderline_id for line in order.lines)
                is_continuous = (
                    previous_order
                    and is_refund == previous_is_refund
                    and order.sequence_number == previous_order.sequence_number + 1
                    and reference and previous_reference
                    and reference['device'] == previous_reference['device']
                    and int(reference['number']) == int(previous_reference['number']) + 1
                )
                if is_continuous:
                    config_line_ids[-1].append(order.id)
                else:
                    config_line_ids.append([order.id])
                previous_order = order
                previous_reference = reference
                previous_is_refund = is_refund

            lines_per_config[config] = [
                pos_order_ids.browse(line_ids) for line_ids in config_line_ids
            ]

        return lines_per_config

    def _get_record_rounded_base_lines(self, record):
        """
        Little helper to return the rounded base line for a record.
        It is extracted in order to allow extending the logic to support other business models.
        :param record: The record from which to get the base lines.
        :return: The rounder base line for the provided record.
        """
        if record and record._name == 'pos.order':
            AccountTax = self.env["account.tax"]
            base_lines = record.lines._prepare_base_lines_for_taxes_computation()
            AccountTax._add_tax_details_in_base_lines(base_lines, self.company_id)
            AccountTax._round_base_lines_tax_details(base_lines, self.company_id)
            return base_lines
        return super()._get_record_rounded_base_lines(record)

    def _base_line_should_be_negated(self, base_line):
        """
        In the PoS, we will merge refunds and their original orders in a single line, in which case the
        refund should reduce the amount of the merged line.
        """
        if base_line["record"] and base_line["record"]._name == 'pos.order.line':
            return base_line["is_refund"]
        return super()._base_line_should_be_negated(base_line)
