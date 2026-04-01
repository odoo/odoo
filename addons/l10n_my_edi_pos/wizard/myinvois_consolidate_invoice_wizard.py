# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import Command, fields, models
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

            lines_per_config = self.env['myinvois.document']._split_pos_orders_in_lines(orders_to_consolidate)

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
        return super()._get_myinvois_document_vals()
