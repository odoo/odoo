import json

from markupsafe import Markup

from odoo import _, api, fields, models


class MailScheduledMessage(models.Model):
    _inherit = 'mail.scheduled.message'

    from_account_move_send = fields.Boolean(compute='_compute_from_account_move_send', store=True)

    # ------------------------------------------------------
    # Compute Methods
    # ------------------------------------------------------

    @api.depends('notification_parameters')
    def _compute_from_account_move_send(self):
        for scheduled_message in self:
            notification_parameters = json.loads(scheduled_message.notification_parameters or '{}')
            scheduled_message.from_account_move_send = notification_parameters.get('from_account_move_send')

    # ------------------------------------------------------
    # Actions
    # ------------------------------------------------------

    def _post_message(self, raise_exception=True):
        # OVERRIDE mail
        # To handle scheduled messages from account.move.send.wizard specifically
        account_scheduled_messages = self.filtered(lambda s: (
            s.model == 'account.move' and
            s.from_account_move_send and
            json.loads(s.notification_parameters or '{}').get('scheduled_move_data')
        ))
        remained_scheduled_messages = self - account_scheduled_messages

        for scheduled_message in account_scheduled_messages:
            scheduled_move_data = json.loads(scheduled_message.notification_parameters or '{}').get('scheduled_move_data')
            move_id = self.env['account.move'].browse(scheduled_message.res_id)

            sending_settings = {
                **{k: v for k, v in scheduled_move_data.items() if k in self._account_get_scheduled_move_data_whitelist()},
                'pdf_report': self.env['ir.actions.report'].browse(scheduled_move_data.get('pdf_report')),
                'author_partner_id': scheduled_message.author_id.id,
            }
            if 'email' in sending_settings['sending_methods']:
                # Add manual attachments from scheduled message to mail_attachments_widget if any,
                # except the attachments which are already in scheduled_move_data from account_move_send_wizard
                move_data_attachments_widget = sending_settings.get('mail_attachments_widget', [])
                attachment_names_from_move_data = [d.get('name') for d in move_data_attachments_widget]
                manual_attachments_widget_data = [
                    {
                        'id': attachment.id,
                        'name': attachment.name,
                        'mimetype': attachment.mimetype,
                        'placeholder': False,
                        'manual': True,
                    }
                    for attachment in scheduled_message.attachment_ids
                    if attachment.name not in attachment_names_from_move_data
                ]
                sending_settings = {
                    **sending_settings,
                    'mail_partner_ids': scheduled_message.partner_ids.ids,
                    'mail_subject': scheduled_message.subject,
                    'mail_body': scheduled_message.body,
                    'mail_template': self.env['mail.template'].browse(sending_settings.get('mail_template')),
                    'mail_attachments_widget': move_data_attachments_widget + manual_attachments_widget_data,
                }

            # The generate and send invoice logic (including any EDI sending methods) with extra manual attachment if any
            attachments = self.env['account.move.send']._generate_and_send_invoices(
                moves=move_id,
                allow_raising=raise_exception,
                **sending_settings,
            )

            if attachments and scheduled_message.from_account_move_send and scheduled_message.is_note:
                move_id._message_log(
                    subject=scheduled_message.subject,
                    body=scheduled_message._account_get_log_note_body(event='sending'),
                )
            scheduled_message.unlink()

        if remained_scheduled_messages:
            super(MailScheduledMessage, remained_scheduled_messages)._post_message(raise_exception)

    # ------------------------------------------------------
    # Business Methods
    # ------------------------------------------------------

    @api.model
    def _account_get_scheduled_move_data_whitelist(self):
        """ Account specific scheduled_move_data parameters which are used when generating and sending invoices.
        """
        return {
            'allow_fallback_pdf',
            'author_user_id',
            'extra_edis',
            'invoice_edi_format',
            'mail_attachments_widget',
            'mail_lang',
            'mail_partner_ids',
            'mail_template',
            'pdf_report',
            'sending_methods',
        }

    @api.model
    def _account_get_sending_method_and_edi_data_from_scheduled_messages(self, move):
        """ To get the sending methods and edis data from scheduled messages of move
            :return: A dict with the following keys:
                - sending_methods: A set of invoice sending methods for which the message is already scheduled
                - extra_edis:      A set of invoice EDI methods for which the message is already scheduled
        """
        moves_data = []
        sending_methods = set()
        extra_edis = set()

        scheduled_messages = self.env['mail.scheduled.message'].search([
            ('from_account_move_send', '=', True),
            ('notification_parameters', '!=', False),
            ('res_id', '=', move.id)
        ])
        for scheduled_message in scheduled_messages:
            if scheduled_move_data := json.loads(scheduled_message.notification_parameters or '{}').get('scheduled_move_data'):
                moves_data.append(scheduled_move_data)

        for move_data in moves_data:
            # Exclude 'email' as it is necessary to allow scheduling multiple emails at once
            sending_methods.update(sending_method for sending_method in move_data.get('sending_methods', []) if sending_method != 'email')
            extra_edis.update(move_data.get('extra_edis', []))

        return {
            'sending_methods': sending_methods,
            'extra_edis': extra_edis,
        }

    def _account_get_log_note_body(self, event):
        """ To get the body of the log note to post on the move for the scheduled message with EDI or other sending methods,
            based on the event
        """
        self.ensure_one()
        scheduled_move_data = json.loads(self.notification_parameters or '{}').get('scheduled_move_data')
        body = self.body
        user_name = self.env.user.name
        if edi_methods := scheduled_move_data.get('extra_edis', []):
            all_extra_edis = self.env['account.move.send']._get_all_extra_edis()
            edi_labels = ", ".join(
                all_extra_edis.get(extra_edi, {}).get('label')
                for extra_edi in edi_methods
                if extra_edi in all_extra_edis and 'label' in all_extra_edis[extra_edi]
            )
            if event == 'sending':
                body = Markup("<p>%s</p>") % (_(
                        'The scheduled request for %s is sent.',
                        Markup("<strong>{}</strong>").format(edi_labels),
                    ))
            elif event == 'cancellation':
                body = Markup("<p>%s</p>") % _(
                    'The scheduled request for %(edi)s is cancelled by %(user)s.',
                    edi=Markup("<strong>{}</strong>").format(edi_labels),
                    user=user_name,
                )
        if other_sending_methods := set(scheduled_move_data.get('sending_methods', [])) - {'email'}:
            methods = dict(self.env['ir.model.fields'].get_field_selection('res.partner', 'invoice_sending_method'))
            methods_labels = ", ".join(
                methods.get(sending_method, '')
                for sending_method in other_sending_methods
                if sending_method in methods
            )
            if event == 'sending':
                body = Markup("<p>%s</p>") % (_(
                    'The scheduled %s method is sent.',
                    Markup("<strong>{}</strong>").format(methods_labels),
                ))
            elif event == 'cancellation':
                body = Markup("<p>%s</p>") % _(
                    'The scheduled %(other)s method is cancelled by %(user)s.',
                    other=Markup("<strong>{}</strong>").format(methods_labels),
                    user=user_name,
                )
        return body

    def account_log_cancellation(self):
        """ Post a log note on the move when the scheduled messages with EDI or other sending methods are cancelled by user.
        """
        moves = self.env['account.move'].browse(self.filtered(
            lambda s: (s.model == 'account.move')).mapped('res_id')
        )
        for scheduled_message in self.filtered(lambda s: (
            s.model == 'account.move' and
            s.from_account_move_send and
            s.is_note
        )):
            self.env['account.move'].with_prefetch(moves).browse(scheduled_message.res_id)._message_log(
                author_id=scheduled_message.author_id.id,
                body=scheduled_message._account_get_log_note_body(event='cancellation'),
            )
