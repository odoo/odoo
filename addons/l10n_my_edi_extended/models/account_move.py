# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import time
from collections import defaultdict

import werkzeug

from odoo import fields, models, api, _, SUPERUSER_ID
from odoo.exceptions import UserError
from odoo.tools.image import image_data_uri


class AccountMove(models.Model):
    _inherit = "account.move"

    # ------------------
    # Fields declaration
    # ------------------

    l10n_my_edi_invoice_long_id = fields.Char(
        string="MyInvois Long ID",
        copy=False,
        readonly=True,
    )
    l10n_my_invoice_need_edi = fields.Boolean(
        compute='_compute_l10n_my_invoice_need_edi',
        export_string_translation=False,
    )

    # --------------------------------
    # Compute, inverse, search methods
    # --------------------------------

    @api.depends('move_type', 'state', 'country_code', 'company_id')
    def _compute_l10n_my_invoice_need_edi(self):
        for move in self:
            # We return true for malaysian invoices which are not sent yet, sent but awaiting validation or valid.
            move.l10n_my_invoice_need_edi = bool(
                move.is_invoice()
                and move.state == 'posted'
                and move.country_code == 'MY'
                and move.l10n_my_edi_state in (False, 'in_progress', 'valid')
                and move.company_id.l10n_my_edi_proxy_user_id
            )

    def _get_name_invoice_report(self):
        # EXTENDS 'account'
        if self.l10n_my_edi_external_uuid:  # Meaning we are a myinvois invoice, meaning we need to embed the qr code.
            # As we add the view in stable, we need to check that it exists.
            if self.env.ref('l10n_my_edi_extended.report_invoice_document', raise_if_not_found=False):
                return 'l10n_my_edi_extended.report_invoice_document'
        return super()._get_name_invoice_report()

    # --------------
    # Action methods
    # --------------

    def action_invoice_sent(self):
        """ The wizard should not be available for invoices sent to MyInvois but not yet validated.
        This is because before validation the ID used for the QR code is not available and the user should NOT send the invoice yet.
        """
        self.ensure_one()

        if self.l10n_my_edi_state == 'in_progress':
            raise UserError(_('You cannot send invoices that are currently being validated.\nPlease wait for the validation to complete.'))

        return super().action_invoice_sent()

    # ----------------
    # Business methods
    # ----------------

    def _update_validation_fields(self, validation_result):
        """ Extended to update the long id as well. """
        # EXTENDS 'l10n_my_edi'
        super()._update_validation_fields(validation_result)
        self.l10n_my_edi_invoice_long_id = validation_result['long_id']

    def _generate_myinvois_qr_code(self):
        """ Generate the qr code which should be embedded into the invoices PDF """
        self.ensure_one()

        if not self.l10n_my_edi_invoice_long_id:  # Only valid invoices have a long id
            return None

        # We need to add the portal url to the qr
        proxy_user = self._l10n_my_edi_ensure_proxy_user()
        if proxy_user.edi_mode == 'prod':
            portal_url = "myinvois.hasil.gov.my"
        else:
            portal_url = "preprod.myinvois.hasil.gov.my"

        try:
            qr_code = self.env['ir.actions.report'].barcode(
                barcode_type='QR',
                width=128,
                height=128,
                humanreadable=1,
                value=f'https://{portal_url}/{self.l10n_my_edi_external_uuid}/share/{self.l10n_my_edi_invoice_long_id}',
            )
        except (ValueError, AttributeError):
            raise werkzeug.exceptions.HTTPException(description='Cannot convert into QR Code.')

        return image_data_uri(base64.b64encode(qr_code))

    def action_l10n_my_edi_send_invoice(self):
        """ Create the xml file (if needed) to be sent to the platform.
        This will replace what is done in send & print.
        """
        self._l10n_my_edi_send_invoice()

    def _l10n_my_edi_send_invoice(self, commit=True):
        # Gather the moves that have to be sent and the xml for each of them.
        moves, xml_contents = self._l10n_my_edi_prepare_moves_to_send()
        # We then push the moves to myinvois.
        self._l10n_my_edi_send_to_myinvois(moves, xml_contents, commit)
        # We need to see if the validation status is already available; otherwise it will be fetched via a cron.
        errors = self._l10n_my_edi_get_status(moves, commit)
        # Finally, we update the move attachments
        for move, xml_content in xml_contents.items():
            if xml_content:
                self.env['ir.attachment'].with_user(SUPERUSER_ID).create({
                    'name': f'{move.name.replace("/", "_")}_myinvois.xml',
                    'raw': xml_content,
                    'mimetype': 'application/xml',
                    'res_model': move._name,
                    'res_id': move.id,
                    'res_field': 'l10n_my_edi_file',  # Binary field
                })
                move.invalidate_recordset(fnames=['l10n_my_edi_file_id', 'l10n_my_edi_file'])
        return errors

    def _l10n_my_edi_prepare_moves_to_send(self):
        AccountMoveSend = self.env['account.move.send']
        xml_contents = defaultdict(list)
        moves = self.env['account.move']
        for move in self:
            if not move.l10n_my_invoice_need_edi or move.l10n_my_edi_state:
                continue

            moves |= move

            if move.l10n_my_edi_file:
                xml_content = base64.b64decode(move.l10n_my_edi_file).decode('utf-8')
            else:
                xml_content, errors = move._l10n_my_edi_generate_invoice_xml()
                if errors:
                    raise UserError(AccountMoveSend._format_error_text({
                        'error_title': _('Error when generating MyInvois file:'),
                        'errors': errors,
                    }))
                xml_content = xml_content.decode('utf-8')
            xml_contents[move] = xml_content
        return moves, xml_contents

    def _l10n_my_edi_send_to_myinvois(self, moves, xml_contents, commit=True):
        AccountMoveSend = self.env['account.move.send']
        if moves and xml_contents:
            errors = moves._l10n_my_edi_submit_documents(xml_contents, commit)

            for move in moves.filtered(lambda m: m in errors):
                move.message_post(body=AccountMoveSend._format_error_html({
                    'error_title': _('Error when sending the invoices to the E-invoicing service.'),
                    'errors': errors[move],
                }))

            # At this point we will need to commit as we reached the api, and we could have a mix of failed and valid invoice.
            if commit and moves._can_commit():
                self._cr.commit()

            # We already logged the details on the invoice(s) and saved the api results. If we send a single invoice, we can safely raise now.
            if errors and len(moves) == 1:
                raise UserError(AccountMoveSend._format_error_text({
                    'error_title': _('Error when sending the invoices to the E-invoicing service.'),
                    'errors': errors[moves],
                }))

    def _l10n_my_edi_get_status(self, moves, commit=True):
        AccountMoveSend = self.env['account.move.send']
        retry = 0
        errors, any_in_progress = moves._l10n_my_edi_fetch_updated_statuses(commit)
        while any_in_progress and retry < 3:
            if self._can_commit():
                time.sleep(1 + retry)  # We wait a while before retrying, only when not in test mode
            errors, any_in_progress = moves._l10n_my_edi_fetch_updated_statuses(commit)
            retry += 1
        # While technically an in_progress status is not an error, it won't hurt much to display it as such.
        # The "error" message in this case should be clear enough.
        for move in moves.filtered(lambda m: m in errors):
            move.message_post(body=AccountMoveSend._format_error_html({
                'error_title': _('Error when sending the invoices to the E-invoicing service.'),
                'errors': errors[move],
            }))
        # We commit again if possible, to ensure that the invoice status is set in the database in case of errors later.
        if commit and self._can_commit():
            self._cr.commit()

        return errors
