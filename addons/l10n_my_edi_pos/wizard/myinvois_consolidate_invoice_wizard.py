# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import Command, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import split_every

MAX_LINE_COUNT_PER_INVOICE = 100


class MyInvoisConsolidateInvoiceWizard(models.TransientModel):
    _inherit = 'myinvois.consolidate.invoice.wizard'

    # ------------------
    # Fields declaration
    # ------------------

    consolidation_type = fields.Selection(
        selection_add=[
            ('pos', 'PoS Order')
        ],
        ondelete={'pos': 'cascade'},
    )

    # ----------------
    # Business methods
    # ----------------

    def _get_myinvois_document_vals(self):
        """
        Prepare and return a list of dicts containing the values needed to create the consolidated invoices for the
        records inbetween the provided dates.
        :return: A list of dicts used to create the consolidated invoices.
        """
        self.ensure_one()
        if self.consolidation_type == 'pos':
            orders_to_consolidate = self.env['pos.order'].search([
                ("state", "=", "done"),
                ("account_move", "=", False),
                ('date_order', '>=', self.date_from),
                ('date_order', '<=', self.date_to),
            ])
            orders_to_consolidate = orders_to_consolidate.filtered(lambda o: not o.consolidated_invoice_ids or all(ci.myinvois_state == 'cancelled' for ci in o.consolidated_invoice_ids))
            if not orders_to_consolidate:
                raise ValidationError(self.env._('Invalid Operation. No order to consolidate.'))

            lines_per_config = self._separate_orders_in_lines(orders_to_consolidate)

            # We now know the amount of lines; we want to create one consolidated invoice per 100 lines.
            consolidated_invoice_vals = []
            for config, lines in lines_per_config.items():
                for line_batch in split_every(MAX_LINE_COUNT_PER_INVOICE, lines, list):
                    orders = self.env['pos.order'].union(*line_batch)
                    consolidated_invoice_vals.append({
                        'pos_order_ids': [Command.set(orders.ids)],
                        'company_id': config.company_id.id,
                        'currency_id': config.currency_id.id,
                        'pos_config_id': config.id,
                    })
            return consolidated_invoice_vals
        else:
            return super()._get_myinvois_document_vals()

    @api.model
    def _separate_orders_in_lines(self, pos_order_ids):
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
        sorted_order = pos_order_ids.sorted(reverse=True)
        all_orders_per_config = sorted_order.session_id.order_ids.sorted(reverse=True).grouped('config_id')
        # During the loop, we want to gather "lines".
        # One line can be comprised of any number of orders as long as they are continuous.
        continuous_orders = self.env['pos.order']
        for config, orders in all_orders_per_config.items():
            config_lines = []
            for order in orders:
                if continuous_orders and order not in pos_order_ids:
                    config_lines.append(continuous_orders)
                    continuous_orders = self.env['pos.order']
                elif order in pos_order_ids:
                    continuous_orders |= order

            # We should group by POS config, as this is where the sequence is expected to be continuous.
            if continuous_orders:
                config_lines.append(continuous_orders)
                continuous_orders = self.env['pos.order']
            lines_per_config[config] = config_lines

        return lines_per_config
