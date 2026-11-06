from odoo import fields, models, modules
from odoo.addons.l10n_gr_edi_e_invoo_bridge.exceptions import EInvooAuthenticationError, EInvooRequestError
from odoo.addons.l10n_gr_edi_e_invoo_bridge.models.account_move import E_INVOO_TOKEN_NOT_SET


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _l10n_gr_edi_get_pre_error_dict(self):
        # OVERRIDE 'l10n_gr_edi_delivery_note'
        errors = super()._l10n_gr_edi_get_pre_error_dict()
        if not self.company_id.sudo().l10n_gr_edi_methodoos_api_token:
            errors['l10n_gr_edi_missing_methodoos_token'] = {
                'message': str(E_INVOO_TOKEN_NOT_SET),
                'action_text': self.env._("View Settings"),
                'action': {
                    'name': self.env._("Settings"),
                    'type': 'ir.actions.act_url',
                    'target': 'self',
                    'url': '/odoo/settings#l10n_gr_edi_aade_settings',
                },
            }
        return errors

    def _l10n_gr_edi_prepare_delivery_note_e_invoo_request(self, invoice_datetime):
        self.ensure_one()

        xml_vals = self._l10n_gr_edi_get_pickings_xml_vals()
        xml_content = self.env['l10n_gr_edi.document']._l10n_gr_edi_generate_xml_content('l10n_gr_edi.mydata_invoice', xml_vals)

        return {
            'xml': xml_content.decode('ISO-8859-7'),
            'invoice_name': self.name,
            'invoice_amount_total': 0,  # As it is a Delivery Note, amount should always be 0
            'invoice_datetime': fields.Datetime.to_string(invoice_datetime),
            'invoice_id': f"{self.env['ir.config_parameter'].sudo().get_param('database.uuid')}-{self.id}",
            'issue_date': fields.Date.to_string(self.date),
        }

    def _l10n_gr_edi_prepare_delivery_note_submission(self):
        self.ensure_one()
        self.env['res.company']._with_locked_records(self)

        # Recheck after locking in case another worker already sent it
        # We order in state desc so that if there is one sent doc it will return it first and otherwise return te pending
        # We want to reuse pending submission to keep timestamp and exact XML on retry
        document = self.env['l10n_gr_edi.document'].search([
            ('picking_id', '=', self.id),
            ('state', 'in', ('delivery_note_sent', 'delivery_note_pending')),
        ], order='state desc', limit=1)

        if document.state == 'delivery_note_sent':
            return None
        document_created = False
        attachment_created = False

        if not document:
            document = self.env['l10n_gr_edi.document'].create({
                'move_id': self.id,
                'state': 'delivery_note_pending',
            })
            document_created = True

        request_values = self._l10n_gr_edi_prepare_delivery_note_e_invoo_request(document.datetime)
        if document.attachment_id:
            request_values['xml'] = document.attachment_id.sudo().raw.decode('utf-8')
        else:
            document.attachment_id = self.env['ir.attachment'].sudo().create({
                'name': f"mydata_delivery_note_{self.name.replace('/', '_')}.xml",
                'res_model': document._name,
                'res_id': document.id,
                'raw': request_values['xml'].encode('utf-8'),
                'type': 'binary',
                'mimetype': 'application/xml',
            })
            attachment_created = True

        if (document_created or attachment_created) and not modules.module.current_test:
            self.env.cr.commit()
            # The commit released the invoice lock; reacquire it before contacting the provider.
            self.env['res.company']._with_locked_records(self)

        return document, request_values

    def _l10n_gr_edi_send_delivery_note(self):
        # OVERRIDE 'l10n_gr_edi_delivery_note'
        self.ensure_one()
        api_token = self.company_id.sudo().l10n_gr_edi_methodoos_api_token
        submission = self._l10n_gr_edi_prepare_delivery_note_submission()
        if not submission:
            return

        document, request_values = submission
        try:
            result = self.env['account.move']._l10n_gr_edi_issue_invoice(
                api_token,
                test_env=self.company_id.l10n_gr_edi_test_env,
                request_values=request_values,
            )
        except EInvooAuthenticationError as e:
            document.write({
                'state': 'invoice_error',
                'message': str(e),
            })
        except EInvooRequestError as e:
            document.message = str(e)
        else:
            self._l10n_gr_edi_handle_invoice_proxy_result(document, result)

        if not modules.module.current_test:
            self.env.cr.commit()
