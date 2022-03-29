# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ApplicantSendMail(models.TransientModel):
    _name = 'applicant.send.mail'
    _inherit = 'mail.composer.mixin'
    _description = 'Send mails to applicants'

    applicant_ids = fields.Many2many('hr.applicant', string='Applications', required=True)
    author_id = fields.Many2one('res.partner', 'Author', required=True, default=lambda self: self.env.user.partner_id.id)

    @api.depends('subject')
    def _compute_render_model(self):
        self.render_model = 'hr.applicant'

    def action_send(self):
        self.ensure_one()

        without_emails = self.applicant_ids.filtered(lambda a: not a.email_from or (a.partner_id and not a.partner_id.email))
        if without_emails:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'danger',
                    'message': _("The following applicants are missing an email address: %s.", ', '.join(without_emails.mapped(lambda a: a.partner_name or a.name))),
                }
            }

        for applicant in self.applicant_ids:
            if not applicant.partner_id:
                applicant.partner_id = self.env['res.partner'].create({
                    'is_company': False,
                    'type': 'private',
                    'name': applicant.partner_name,
                    'email': applicant.email_from,
                    'phone': applicant.partner_phone,
                    'mobile': applicant.partner_mobile,
                })

            applicant.message_post(
                subject=self.subject,
                body=self.body,
                message_type='comment',
                email_from=self.author_id.email,
                email_layout_xmlid='mail.mail_notification_light',
                partner_ids=applicant.partner_id.ids,
            )
