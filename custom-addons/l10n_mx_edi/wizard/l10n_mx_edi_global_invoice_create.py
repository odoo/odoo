from odoo import api, fields, models, Command
from odoo.addons.l10n_mx_edi.models.l10n_mx_edi_document import GLOBAL_INVOICE_PERIODICITY_DEFAULT_VALUES


class L10nMxEdiGlobalInvoiceCreate(models.Model):
    _name = 'l10n_mx_edi.global_invoice.create'
    _description = "Create a global invoice"

    move_ids = fields.Many2many(comodel_name='account.move')

    periodicity = fields.Selection(
        **GLOBAL_INVOICE_PERIODICITY_DEFAULT_VALUES,
        required=True,
    )

    @api.model
    def default_get(self, fields_list):
        # EXTENDS 'base'
        results = super().default_get(fields_list)

        if 'move_ids' in results:
            source_invoices = self.env['account.move'].browse(results['move_ids'][0][2])
            invoices = source_invoices._l10n_mx_edi_check_invoices_for_global_invoice()
            results['move_ids'] = [Command.set(invoices.ids)]

        return results

    def action_create_global_invoice(self):
        self.ensure_one()
        self.move_ids._l10n_mx_edi_cfdi_global_invoice_try_send(periodicity=self.periodicity)
