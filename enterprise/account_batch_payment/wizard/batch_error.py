# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, _


class BatchErrorWizard(models.TransientModel):
    _name = 'account.batch.error.wizard'
    _description = "Batch payments error reporting wizard"

    batch_payment_id = fields.Many2one(comodel_name='account.batch.payment', required=True, help="The batch payment generating the errors and warnings displayed in this wizard.")
    error_line_ids = fields.One2many(comodel_name='account.batch.error.wizard.line', inverse_name='error_wizard_id')
    warning_line_ids = fields.One2many(comodel_name='account.batch.error.wizard.line', inverse_name='warning_wizard_id')
    show_remove_options = fields.Boolean(required=True, help="True if and only if the options to remove the payments causing the errors or warnings from the batch should be shown")

    @api.model
    def create_from_errors_list(self, batch, errors_list, warnings_list):
        rslt = self.create({'batch_payment_id': batch.id, 'show_remove_options': batch.export_file})
        self._create_error_wizard_lines(rslt.id, 'error_wizard_id', errors_list)
        self._create_error_wizard_lines(rslt.id, 'warning_wizard_id', warnings_list)
        return rslt

    @api.model
    def _create_error_wizard_lines(self, wizard_id, wizard_link_field, entries):
        wizard_line = self.env['account.batch.error.wizard.line']
        for entry in entries:
            wizard_line.create({
                wizard_link_field: wizard_id,
                'description': entry['title'],
                'help_message': entry.get('help', None),
                'payment_ids': [(6, False, entry['records'].ids)],
            })

    def proceed_with_validation(self):
        self.ensure_one()
        return self.batch_payment_id._send_after_validation()

class BatchErrorWizardLine(models.TransientModel):
    _name = 'account.batch.error.wizard.line'
    _description = "Batch payments error reporting wizard line"

    description = fields.Char(string="Description", required=True)
    help_message = fields.Char(string="Help")
    payment_ids = fields.Many2many(string='Payments', comodel_name='account.payment', required=True)
    error_wizard_id = fields.Many2one(comodel_name='account.batch.error.wizard')
    warning_wizard_id = fields.Many2one(comodel_name='account.batch.error.wizard')
    # Whether or not this line should display a button allowing to remove its related payments from the batch
    show_remove_button = fields.Boolean(compute="_compute_show_remove_button")

    def _compute_show_remove_button(self):
        for record in self:
            record.show_remove_button = record.error_wizard_id.show_remove_options or record.warning_wizard_id.show_remove_options

    def open_payments(self):
        return self.payment_ids._get_records_action(name=_('Payments in Error'))

    def remove_payments_from_batch(self):
        for payment in self.payment_ids:
            payment.batch_payment_id = None

        # We try revalidating the batch if we still have payments for it (we hence do nothing for empty batches)
        batch = (self.error_wizard_id or self.warning_wizard_id).batch_payment_id
        if batch.payment_ids:
            return batch.validate_batch()
