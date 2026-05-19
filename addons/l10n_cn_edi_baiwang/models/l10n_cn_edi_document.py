# models/l10n_cn_edi_document.py
from odoo import fields, models, api
from .baiwang_client import BaiwangClient
import logging

_logger = logging.getLogger(__name__)

class L10nCnEdiDocument(models.Model):
    _name = 'l10n_cn_edi.document'
    _description = 'Baiwang EDI Document (Red Form)'
    _order = 'create_date desc'

    move_id = fields.Many2one('account.move', string="Credit Note", required=True, ondelete='cascade')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('red_form_pending', 'Pending Counterpart Confirmation'),
        ('red_form_confirmed', 'Red Form Confirmed'),
        ('failed', 'Failed/Rejected')
    ], default='draft', tracking=True)

    baiwang_uuid = fields.Char(string="Red Form UUID", copy=False)
    baiwang_red_form_number = fields.Char(string="Red Form Number", copy=False)
    error_message = fields.Text(string="Error Details")

    @api.model
    def _cron_check_red_form_status(self):
        """
        Scheduled action to poll Baiwang for the status of pending Red Forms.
        """
        # Find all pending documents
        pending_docs = self.search([('state', '=', 'red_form_pending'), ('baiwang_uuid', '!=', False)])

        if not pending_docs:
            return

        _logger.info(f"Baiwang EDI: Found {len(pending_docs)} pending red forms. Polling for status...")

        for doc in pending_docs:
            company = doc.move_id.company_id

            # Setup Client
            client = BaiwangClient(
                app_key=company.l10n_cn_baiwang_app_key,
                app_secret=company.l10n_cn_baiwang_app_secret,
                salt=company.l10n_cn_baiwang_salt,
            )

            # Payload to check status using UUID
            # (Note: Using operate or query endpoint depending on exact Baiwang specs, assuming redforminfo here)
            payload = {
                "taxNo": company.vat,
                "redConfirmUuid": doc.baiwang_uuid
            }

            try:
                response = client.call_api("baiwang.output.redinvoice.redforminfo", payload, company.l10n_cn_baiwang_cached_token)

                if response.get("success"):
                    resp_data = response.get("response", {})
                    # Get the confirmState from the response
                    confirm_state = resp_data.get("confirmState") 

                    if confirm_state in ('01', '04'):
                        # 01-无需确认, 04-购销双方已确认
                        red_form_no = resp_data.get("redConfirmNo", "")
                        doc.write({
                            'state': 'red_form_confirmed',
                            'baiwang_red_form_number': red_form_no
                        })
                        # Log success on the invoice chatter
                        doc.move_id.message_post(body=f"Red Form Confirmed by counterpart! Red Form No: {red_form_no}. You may now confirm this Credit Note.")

                    elif confirm_state in ('02', '03'):
                        # 02-待购方确认, 03-待销方确认
                        # Still pending, do nothing
                        pass

                    elif confirm_state in ('05', '06', '07', '08', '09', '10'):
                        # Various rejected/cancelled/expired states
                        doc.write({
                            'state': 'failed',
                            'error_message': f"Rejected/Cancelled by Baiwang. State Code: {confirm_state}"
                        })
                        doc.move_id.message_post(body=f"Red Form Request Failed/Rejected. State code: {confirm_state}.")
                else:
                    # API returned success=False
                    error_msg = response.get("errorResponse", {}).get("message", "Unknown Error")
                    doc.write({'state': 'failed', 'error_message': error_msg})

            except Exception as e:
                # Catch network errors so the cron job doesn't completely crash for other records
                _logger.error(f"Baiwang EDI: Network error while polling UUID {doc.baiwang_uuid}. Error: {str(e)}")
