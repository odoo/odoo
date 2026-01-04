import pytz

from odoo import api, fields, models

from ..tools import _mer_api_reject_with_id, _mer_api_update_document_process_status


class L10nHrMojEracunRejectInvoice(models.TransientModel):
    _name = 'l10n_hr_edi.mojeracun_reject_wizard'
    _description = "MojEracun Reject Invoice Wizard"

    move_id = fields.Many2one(comodel_name='account.move', required=True)
    rejection_type = fields.Selection(
        string="Rejection reason type",
        selection=[
            ('N', "'N' - Data discrepancy that does not affect tax calculation"),
            ('U', "'U' - Data discrepancy that affects tax calculation"),
            ('O', "'O' - Other"),
        ],
        required=True
    )
    rejection_description = fields.Char(string="Rejection reason description", required=True)

    @api.model
    def default_get(self, fields_list):
        # EXTENDS 'base'
        results = super().default_get(fields_list)
        if 'move_id' in fields_list and 'move_id' not in results:
            move_id = self.env.context.get('active_ids', [])[0]
            results['move_id'] = move_id
        return results

    def button_reject_invoice(self):
        if self.move_id.l10n_hr_mer_document_eid:
            response = _mer_api_reject_with_id(
                self.move_id.company_id,
                self.move_id.l10n_hr_mer_document_eid,
                fields.Datetime.now(pytz.timezone('Europe/Zagreb')).strftime("%Y-%m-%dT%H:%M:%S"),
                self.rejection_type,
                self.rejection_description,
            )
            attachment = self.env["ir.attachment"].create(
                {
                    "name": f"mojeracun_{response['electronicId']}_rejection.xml",
                    "raw": response['encodedXml'],
                    "type": "binary",
                    "mimetype": "application/xml",
                }
            )
            attachment.write({'res_model': 'account.move', 'res_id': self.move_id.id})
            self.move_id._message_log(
                body=self.env._(
                    "%(timestamp)s: eRacun document (ElectroicId: %(electronic_id)s) has been rejected successfully.",
                    timestamp=response['fiscalizationTimestamp'], electronic_id=self.move_id.l10n_hr_mer_document_eid,
                ),
                attachment_ids=attachment.ids,
            )
            self.move_id.l10n_hr_edi_addendum_id.business_document_status = '1'
            _mer_api_update_document_process_status(
                self.move_id.company_id,
                self.move_id.l10n_hr_mer_document_eid,
                '1',
                self.rejection_description,
            )
            self.move_id.button_cancel()
