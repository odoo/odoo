from odoo import api, fields, models
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    l10n_ar_delivery_guide_number = fields.Char(
        string="Delivery Guide No.",
        copy=False,
        readonly=True,
    )
    l10n_ar_cai_data = fields.Json(string="CAI Data", copy=False)
    l10n_ar_allow_generate_delivery_guide = fields.Boolean(
        compute="_compute_l10n_ar_delivery_guide_flags",
    )
    l10n_ar_allow_send_delivery_guide = fields.Boolean(
        compute="_compute_l10n_ar_delivery_guide_flags",
    )
    l10n_ar_delivery_guide_cron_user_id = fields.Many2one(
        comodel_name="res.users",
        readonly=True,
        copy=False,
    )

    # === COMPUTE METHODS === #

    @api.depends('state', 'l10n_ar_delivery_guide_number', 'picking_type_id.l10n_ar_document_type_id')
    def _compute_l10n_ar_delivery_guide_flags(self):
        """
        Compute flags for allowing delivery guide generation and sending.
        - Generation allowed if: state is 'done', document type exists, and no guide number.
        - Send allowed if: guide number exists.
        """
        for picking in self:
            has_doc_type = bool(picking.picking_type_id.l10n_ar_document_type_id)
            picking.l10n_ar_allow_generate_delivery_guide = (
                picking.state == 'done' and has_doc_type and not picking.l10n_ar_delivery_guide_number
            )
            picking.l10n_ar_allow_send_delivery_guide = bool(picking.l10n_ar_delivery_guide_number)

    # === BUSINESS METHODS === #

    def l10n_ar_action_create_delivery_guide(self):
        """
        Create the delivery guide number and store CAI data for the selected stock pickings.
        """
        already_generated = not_done = no_doc_type = self.env['stock.picking']
        for picking in self:
            if picking.l10n_ar_delivery_guide_number:
                already_generated += picking
            elif picking.state != 'done':
                not_done += picking
            elif not picking.picking_type_id.l10n_ar_document_type_id:
                no_doc_type += picking
        errors = []
        if already_generated:
            errors.append(self.env._("- %(names)s already have a delivery guide.", names=already_generated.mapped('name')))
        if not_done:
            errors.append(self.env._("- %(names)s must be validated before generating a delivery guide.", names=not_done.mapped('name')))
        if no_doc_type:
            errors.append(self.env._("- The operation types on the deliveries are not configured for delivery guides: %(names)s.", names=no_doc_type.mapped('name')))
        if errors:
            raise UserError(self.env._("Cannot generate delivery guides for the following transfers:\n%(transfers)s", transfers="\n".join(errors)))

        for picking in self:
            picking_type = picking.picking_type_id
            new_sequence_number = picking_type.l10n_ar_next_delivery_number
            delivery_guide_number = picking_type.l10n_ar_sequence_id.next_by_id()
            if not int(picking_type.l10n_ar_sequence_number_start) <= new_sequence_number <= int(picking_type.l10n_ar_sequence_number_end):
                raise UserError(self.env._("The delivery guide number %s exceeds the range specified in the CAI. Please update the range or use a different CAI with a different range.", delivery_guide_number))
            picking.l10n_ar_delivery_guide_number = delivery_guide_number
            picking.l10n_ar_cai_data = {
                'document_type_id': picking_type.l10n_ar_document_type_id.id,
                'cai_authorization_code': picking_type.l10n_ar_cai_authorization_code,
                'cai_expiration_date': picking_type.l10n_ar_cai_expiration_date.strftime('%Y-%m-%d'),
                'sequence_number_start': picking_type.l10n_ar_sequence_number_start,
                'sequence_number_end': picking_type.l10n_ar_sequence_number_end,
            }

    def l10n_ar_action_send_delivery_guide(self, do_async=False):
        """ Send the delivery guide to the proper partners.
            :param do_async: If True, queue the sending via cron instead of sending immediately."""
        self._l10n_ar_validate_send_delivery_guide()
        if not do_async:
            self._l10n_ar_send_delivery_guide(force_send=True)
            return None
        self.l10n_ar_delivery_guide_cron_user_id = self.env.user
        self.env.ref('l10n_ar_stock.ir_cron_l10n_ar_send_delivery_guide')._trigger()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'info',
                'title': self.env._('Processing Delivery Guides'),
                'message': self.env._('Delivery guides are being sent in the background.'),
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }

    def _l10n_ar_validate_send_delivery_guide(self, do_async=False):
        """ Validate that all pickings in self are eligible for sending delivery guides. """
        no_doc_type = no_number = no_email = already_queued = self.env['stock.picking']
        for picking in self:
            if not picking.picking_type_id.l10n_ar_document_type_id:
                no_doc_type += picking
            elif not picking.l10n_ar_delivery_guide_number:
                no_number += picking
            elif not picking.partner_id.email:
                no_email += picking
            elif picking.l10n_ar_delivery_guide_cron_user_id:
                already_queued += picking
        if do_async:
            # We don't care about already_queued as this is call during the queued cron.
            return {
                'no_doc_type': no_doc_type,
                'no_number': no_number,
                'no_email': no_email,
                'all_errors': no_doc_type + no_number + no_email,
            }
        errors = []
        if no_doc_type:
            errors.append(self.env._("- The operation types on the deliveries are not configured for delivery guides: %(names)s.", names=no_doc_type.mapped('name')))
        if no_number:
            errors.append(self.env._("- No delivery guide has been generated yet for the following deliveries: %(names)s.", names=no_number.mapped('name')))
        if no_email:
            errors.append(self.env._("- The contacts on the following deliveries have no email address: %(names)s.", names=no_email.mapped('name')))
        if already_queued:
            errors.append(self.env._("- The following deliveries are already queued for sending: %(names)s.", names=already_queued.mapped('name')))
        if errors:
            raise UserError(self.env._("Cannot send delivery guides for the following transfers:\n%(transfers)s", transfers="\n".join(errors)))
        return {}

    def _l10n_ar_send_delivery_guide(self, force_send=False):
        """ Send the delivery guide email for each picking in self.

        PDFs are rendered in a single wkhtmltopdf call and split per record,
        which is dramatically faster than per-record rendering for batches.
        """
        template = self.env.ref('l10n_ar_stock.email_template_ar_remitos_delivery_guide')
        pdf_action = self.env.ref('l10n_ar_stock.action_delivery_guide_report_pdf')

        pdf_contents = self._l10n_ar_render_delivery_guide_pdfs(pdf_action)

        attachment_vals = [{
            'name': f'Remito - {picking.l10n_ar_delivery_guide_number}.pdf',
            'type': 'binary',
            'raw': pdf_contents[picking.id],
            'res_model': self._name,
            'res_id': picking.id,
            'mimetype': 'application/pdf',
        } for picking in self]
        attachments = self.env['ir.attachment'].create(attachment_vals)

        for picking, attachment in zip(self, attachments):
            picking.with_context(
                mail_notify_force_send=force_send,
            ).message_post_with_source(
                template,
                subtype_xmlid='mail.mt_comment',
                email_layout_xmlid='mail.mail_notification_layout_with_responsible_signature',
                attachment_ids=attachment.ids,
            )

    def _l10n_ar_render_delivery_guide_pdfs(self, pdf_action):
        """ Batch-render delivery guide PDFs, returning {picking_id: pdf_bytes}.

        Falls back to per-record rendering if the batched merge step fails
        (wkhtmltopdf can refuse to merge multiple documents on unpatched QT,
        and the merge helper raises UserError when pypdf can't stitch the
        intermediate PDFs together).
        """
        report_sudo = self.env['ir.actions.report'].sudo()
        try:
            collected_streams, report_type = report_sudo._pre_render_qweb_pdf(pdf_action, self.ids)
            if report_type != 'pdf':
                # In test environments _pre_render_qweb_pdf falls back to
                # _render_qweb_html which returns raw bytes, not a stream dict.
                return {picking.id: collected_streams for picking in self}
            return {
                res_id: stream_data['stream'].getvalue()
                for res_id, stream_data in collected_streams.items()
                if stream_data.get('stream')
            }
        except UserError:
            pdf_contents = {}
            for picking in self:
                pdf_content, _unused = report_sudo._render_qweb_pdf(pdf_action, picking.id)
                pdf_contents[picking.id] = pdf_content
            return pdf_contents

    def _l10n_ar_handle_cron_failures(self, errors):
        """ Dequeue failed records: log in chatter, notify users, clear cron field. """
        failed = errors['all_errors']
        error_messages = {
            'no_doc_type': self.env._("Delivery guide could not be sent: the operation type is not configured for delivery guides."),
            'no_number': self.env._("Delivery guide could not be sent: no delivery guide number has been generated."),
            'no_email': self.env._("Delivery guide could not be sent: the contact has no email address."),
        }
        for error_key, message in error_messages.items():
            for picking in errors.get(error_key, self.env['stock.picking']):
                picking.message_post(body=message, message_type='notification')
        for user, user_pickings in failed.grouped('l10n_ar_delivery_guide_cron_user_id').items():
            user._bus_send(
                'account_notification',
                {
                    'type': 'warning',
                    'title': self.env._('Delivery Guide Send Failed'),
                    'message': self.env._(
                        'The following Delivery Guides could not be sent due to validation errors:\n%(errors)s',
                        errors="\n".join(user_pickings.mapped('name')),
                    ),
                    'action_button': {
                        'name': self.env._('Open'),
                        'action_name': self.env._('Failed Delivery Guides'),
                        'model': 'stock.picking',
                        'res_ids': user_pickings.ids,
                    },
                },
            )
        failed.write({'l10n_ar_delivery_guide_cron_user_id': False})

    def _cron_l10n_ar_send_delivery_guide(self, batch_size=50):
        """ Cron method: process queued delivery guide sends in batches. """
        domain = [
            ('l10n_ar_delivery_guide_cron_user_id', '!=', False),
        ]
        records = self.search(domain, order='id asc', limit=batch_size).try_lock_for_update()
        records_len = len(records)
        if not records:
            return

        # Re-validate: fields may have changed since queueing.
        errors = records._l10n_ar_validate_send_delivery_guide(do_async=True)
        if errors.get('all_errors'):
            self._l10n_ar_handle_cron_failures(errors)
            records -= errors['all_errors']

        if not records:
            remaining = self.search_count(domain)
            self.env['ir.cron']._commit_progress(records_len, remaining=remaining)
            return

        pickings_by_user = records.grouped('l10n_ar_delivery_guide_cron_user_id')
        for user, user_pickings in pickings_by_user.items():
            user_pickings.with_user(user)._l10n_ar_send_delivery_guide()

        for user, user_pickings in pickings_by_user.items():
            user._bus_send(
                'account_notification',
                {
                    'type': 'success',
                    'title': self.env._('Delivery Guides Sent'),
                    'message': self.env._('The following Delivery Guide emails have been sent successfully.'),
                    'action_button': {
                        'name': self.env._('Open'),
                        'action_name': self.env._('Sent Delivery Guides'),
                        'model': 'stock.picking',
                        'res_ids': user_pickings.ids,
                    },
                },
            )
        records.write({'l10n_ar_delivery_guide_cron_user_id': False})

        remaining = self.search_count(domain)
        self.env['ir.cron']._commit_progress(records_len, remaining=remaining)
