from odoo import api, fields, models, Command


class L10nMxEdiGlobalInvoiceCreate(models.Model):
    _inherit = 'l10n_mx_edi.global_invoice.create'

    pos_order_ids = fields.Many2many(comodel_name='pos.order')

    @api.model
    def default_get(self, fields_list):
        # EXTENDS 'l10n_mx_edi'
        results = super().default_get(fields_list)

        if 'pos_order_ids' in results:
            source_orders = self.env['pos.order'].browse(results['pos_order_ids'][0][2])
            orders = source_orders._l10n_mx_edi_check_orders_for_global_invoice()
            results['pos_order_ids'] = [Command.set(orders.ids)]
        return results

    def action_create_global_invoice(self):
        # EXTENDS 'l10n_mx_edi'
        self.ensure_one()
        if self.pos_order_ids:
            self.pos_order_ids._l10n_mx_edi_cfdi_global_invoice_try_send(periodicity=self.periodicity)
        else:
            super().action_create_global_invoice()
