# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import _, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError


class L10nVnEdiViettelStockSendWizard(models.TransientModel):
    _name = 'l10n_vn_edi_viettel_stock.send_wizard'
    _description = 'Send Transfer Note to SInvoice'

    picking_id = fields.Many2one(comodel_name='stock.picking', string='Transfer', required=True)
    template_field_ids = fields.One2many(
        comodel_name='l10n_vn_edi_viettel_stock.template_field_line',
        inverse_name='wizard_id',
        string='Template Fields',
    )

    def action_send(self):
        self.ensure_one()

        # Validate required fields before sending
        missing = self.template_field_ids.filtered(lambda l: l.is_required and not l.value)
        if missing:
            raise UserError(_(
                'The following required fields must be filled in:\n%s',
                '\n'.join(f'- {line.key_label}' for line in missing),
            ))

        picking = self.picking_id

        # Generate the transfer note JSON payload using the wizard's custom field lines
        json_data = picking._l10n_vn_edi_generate_transfer_note_json(self.template_field_ids)

        # Store the JSON file as an attachment on the picking
        attachment = self.env['ir.attachment'].with_user(SUPERUSER_ID).create({
            'name': f'{picking.name.replace("/", "_")}_sinvoice.json',
            'raw': json.dumps(json_data, ensure_ascii=False).encode('utf-8'),
            'mimetype': 'application/json',
            'res_model': picking._name,
            'res_id': picking.id,
            'res_field': 'l10n_vn_edi_sinvoice_file_id',
        })
        picking.l10n_vn_edi_sinvoice_file_id = attachment

        # Send to SInvoice
        errors = picking._l10n_vn_edi_send_transfer_note(json_data)
        if errors:
            raise UserError('\n'.join(errors))

        # Fetch the XML and PDF files from SInvoice
        file_errors = picking._l10n_vn_edi_fetch_files()
        if file_errors:
            picking.message_post(body='{title}\n{errors}'.format(
                title=file_errors['error_title'],
                errors='\n'.join(file_errors['errors']),
            ))
