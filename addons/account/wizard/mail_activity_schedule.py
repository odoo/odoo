# Part of Odoo. See LICENSE file for full copyright and licensing details.
from markupsafe import Markup

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools import format_amount, format_date


class MailActivitySchedule(models.TransientModel):
    _inherit = 'mail.activity.schedule'

    request_from_id = fields.Many2one('res.partner')
    document_name = fields.Char(
        'Document Name',
        compute='_compute_document_name',
        store=True,
        readonly=False,
    )
    request_message = fields.Html(
        "Message",
        sanitize_style=True,
        compute="_compute_request_message",
        store=True,
        readonly=False,
    )
    is_request_document_activity = fields.Boolean(compute="_compute_is_request_document_activity")

    @api.depends('is_request_document_activity')
    def _compute_document_name(self):
        for wizard in self:
            if wizard._is_move_request_doc() and not wizard.document_name:
                move_id = self._get_applied_on_records()
                invoice_date = format_date(self.env, move_id.invoice_date) or fields.Date.today()
                amount = format_amount(self.env, move_id.amount_total, move_id.currency_id)
                if move_id.journal_id.type == 'bank':
                    wizard.document_name = _('Missing document for bank transaction of bank account %(bank_account)s dated %(invoice_date)s for the amount of %(amount)s',
                        bank_account=move_id.journal_id.bank_acc_number,
                        invoice_date=invoice_date,
                        amount=amount,
                    )
                else:
                    wizard.document_name = _('Missing document from %(customer)s dated %(invoice_date)s for the amount of %(amount)s',
                        customer=move_id.partner_id.name,
                        invoice_date=invoice_date,
                        amount=amount,
                    )

    @api.depends('is_request_document_activity')
    def _compute_request_message(self):
        for wizard in self:
            if wizard._is_move_request_doc() and not wizard.request_message:
                wizard.request_message = self._get_request_message()

    @api.depends('activity_type_id')
    def _compute_is_request_document_activity(self):
        for wizard in self:
            wizard.is_request_document_activity = wizard.activity_type_id.name == 'Request Document'

    @api.constrains('request_from_id')
    def _check_request_from_id(self):
        for wizard in self:
            if wizard.request_from_id and not wizard.request_from_id.email:
                raise ValidationError(_("The selected 'Request From' must have a valid email address."))

    @api.onchange('is_request_document_activity', 'request_from_id', 'activity_user_id')
    def _onchange_request_message(self):
        if self._is_move_request_doc():
            self.request_message = self._get_request_message()

    def _is_move_request_doc(self):
        return self.is_request_document_activity and self.res_model == 'account.move'

    def _get_request_message(self):
        move_id = self._get_applied_on_records()
        invoice_date = format_date(self.env, move_id.invoice_date) or fields.Date.today()
        amount = format_amount(self.env, move_id.amount_total, move_id.currency_id)
        requestee_from_name = self.request_from_id.name or ''
        user_name = self.activity_user_id.name or ''
        user_email = self.activity_user_id.email or ''
        if move_id.journal_id.type == 'bank':
            return Markup("""
                    <div>
                        <p style="margin: 0px; padding: 0px; font-size: 15px;">
                            Hello {requestee_from_name},
                            <br />
                            {user_name} ({user_email}) asks you to provide the following missing document for bank transaction of bank account {bank_account} dated {date} for the amount of {amount}
                        </p>
                    </div>
                    """).format(
                        requestee_from_name=requestee_from_name,
                        user_name=user_name,
                        user_email=user_email,
                        bank_account=move_id.journal_id.bank_acc_number or '',
                        date=invoice_date,
                        amount=amount,
                        )
        else:
            return Markup("""
                    <div>
                        <p style="margin: 0px; padding: 0px; font-size: 15px;">
                            Hello {requestee_from_name},
                            <br />
                            {user_name} ({user_email}) asks you to provide the following missing document from {customer_name} dated {date} for the amount of {amount}
                        </p>
                    </div>
                    """).format(
                        requestee_from_name=requestee_from_name,
                        user_name=user_name,
                        user_email=user_email,
                        customer_name=move_id.partner_id.name or '',
                        date=invoice_date,
                        amount=amount,
                    )

    def _action_schedule_activities(self):
        context = {}
        if self._is_move_request_doc():
            context.update({
                'mail_activity_quick_update': True,
            })
        activity = self._get_applied_on_records() \
            .with_context(**context) \
            .activity_schedule(
                activity_type_id=self.activity_type_id.id,
                automated=False,
                summary=self.summary,
                note=self.note,
                user_id=self.activity_user_id.id,
                date_deadline=self.date_deadline
            )
        if self._is_move_request_doc():
            requested_document = self.env['account.requested.document'].create({
                'request_activity_id': activity.id,
                'name': self.document_name,
            })
            rendered_mail_body = self._get_mail_body(requested_document)
            mail_body = self.env['mail.render.mixin']._replace_local_links(rendered_mail_body)
            mail = self.env['mail.mail'].sudo().create({
                'author_id': self.activity_user_id.parent_id.id,
                'email_from': self.activity_user_id.email_formatted,
                'email_to': self.request_from_id.email_formatted,
                'subject': self.document_name,
                'body_html': mail_body,
            })
            mail.send()
            self._get_applied_on_records()._message_log(body=self._get_message_body(mail_body))
        return activity

    def _get_mail_body(self, requested_document):
        return self.env['ir.qweb']._render('account.email_request_document_account_move', {
            'user': self.activity_user_id,
            'requested_document': requested_document,
            'request_message': self.request_message,
        })

    def _get_message_body(self, mail_body):
        return Markup("""
        <h6>
            Request Document Email has been sent:
        </h6>
        """) + mail_body
