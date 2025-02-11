# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import Command, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import split_every

MAX_LINE_COUNT_PER_INVOICE = 100


class MyInvoisConsolidateInvoiceWizard(models.TransientModel):
    _name = 'myinvois.consolidate.invoice.wizard'
    _description = 'Consolidate Invoice Wizard'

    # ------------------
    # Fields declaration
    # ------------------

    date_from = fields.Date(
        string='Date From',
        required=True,
    )
    date_to = fields.Date(
        string='Date To',
        required=True,
    )

    # --------------
    # Action methods
    # --------------

    def button_consolidate_orders(self):
        """
        By default, we only consolidated orders that are in the range, done and not invoiced.
        We do allow to also consolidate invoices linked to a cancelled consolidated invoice.

        Note that doing so lock the cancelled invoice into its cancelled state.
        """
        self.ensure_one()
        orders_to_consolidate = self.env['pos.order'].search([
            ("state", "=", "done"),
            ("account_move", "=", False),
            ('date_order', '>=', self.date_from),
            ('date_order', '<=', self.date_to),
        ])
        orders_to_consolidate = orders_to_consolidate.filtered(lambda o: not o.consolidated_invoice_ids or all(ci.myinvois_state == 'cancelled' for ci in o.consolidated_invoice_ids))
        if not orders_to_consolidate:
            raise ValidationError(self.env._('Invalid Operation. No order to consolidate.'))

        lines_per_config = self.env['myinvois.document']._separate_orders_in_lines(orders_to_consolidate)

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
        self.env['myinvois.document'].create(consolidated_invoice_vals)

        return orders_to_consolidate.action_show_consolidated_invoice()
