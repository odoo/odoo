# Part of Odoo. See LICENSE file for full copyright and licensing details.
import itertools

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.tools import date_utils


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

    # -----------------------
    # CRUD, inherited methods
    # -----------------------

    def _get_starting_sequence(self):
        """ In the PoS, a document represents a Consolidated INVoice. """
        self.ensure_one()
        if not self.pos_order_ids:
            return super()._get_starting_sequence()

        return "CINV/%04d/00000" % self.myinvois_issuance_date.year

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
                'views': [(False, 'list'), (False, 'form')],
                'domain': [('id', 'in', self.pos_order_ids.ids)],
            }

        return action_vals

    def action_open_consolidate_invoice_wizard(self):
        """
        Open the wizard, and set a default date_from/date_to based on the current date as well as already existing
        consolidated invoices.
        """
        latest_consolidated_invoice = self.env['myinvois.document'].search([
            ('company_id', '=', self.env.company.id),
            ('myinvois_state', 'in', ['in_progress', 'valid']),
            ('pos_order_ids', '!=', False),
        ], limit=1)
        if latest_consolidated_invoice:
            default_date_from = latest_consolidated_invoice.myinvois_issuance_date + relativedelta(days=1)
        else:
            default_date_from = date_utils.start_of(fields.Date.context_today(self) - relativedelta(months=1), 'month')
        default_date_to = date_utils.end_of(default_date_from, 'month')

        return {
            'name': self.env._('Create Consolidated Invoice'),
            'res_model': 'myinvois.consolidate.invoice.wizard',
            'view_mode': 'form',
            'views': [[False, 'form']],
            'target': 'new',
            'context': {
                'default_date_from': default_date_from,
                'default_date_to': default_date_to,
                'default_consolidation_type': 'pos',
            },
            'type': 'ir.actions.act_window',
        }

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

        :param pos_order_ids: The orders to separate.
        :return: A dict of pos order per config, for each config having a list of recordset each representing a single line in the xml.
        """
        lines_per_config = {}
        # We start by gathering the sessions involved in this process, and loop on their orders.
        sorted_orders_to_consolidated = pos_order_ids.sorted(reverse=True)
        sorted_session_orders = (
            sorted_orders_to_consolidated.session_id.order_ids.sorted(reverse=True)
        )
        # During the loop, we want to gather "lines".
        # One line can be comprised of any number of orders as long as they are continuous.
        continuous_orders = []
        for config, orders in itertools.groupby(sorted_session_orders, key=lambda o: o["config_id"]):
            config_lines = []
            for order in orders:
                if continuous_orders and order not in pos_order_ids:
                    config_lines.append(self.env["pos.order"].browse(continuous_orders))
                    continuous_orders = []
                elif order in pos_order_ids:
                    continuous_orders.append(order.id)

            # We don't mix orders from different configs in a single line as they have different sequences.
            if continuous_orders:
                config_lines.append(self.env["pos.order"].browse(continuous_orders))
                continuous_orders = []
            lines_per_config[config] = config_lines

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
            base_lines = record._prepare_tax_base_line_values()
            AccountTax._add_tax_details_in_base_lines(base_lines, self.company_id)
            AccountTax._round_base_lines_tax_details(base_lines, self.company_id)
            return base_lines
        return super()._get_record_rounded_base_lines(record)
