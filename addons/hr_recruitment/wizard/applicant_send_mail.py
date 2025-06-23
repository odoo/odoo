# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ApplicantSendMail(models.TransientModel):
    _name = 'applicant.send.mail'
    _inherit = ['mail.composer.mixin']
    _description = 'Send mails to applicants'

    applicant_ids = fields.Many2many('hr.applicant', string='Applications', required=True)
    author_id = fields.Many2one('res.partner', 'Author', required=True, default=lambda self: self.env.user.partner_id.id)
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments', readonly=False, store=True, bypass_search_access=True)

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
                    'message': _("The following applicants are missing an email address: %s.", ', '.join(without_emails.mapped(lambda a: a.partner_name or a.display_name))),
                }
            }

        if self.template_id:
            subjects = self._render_field('subject', res_ids=self.applicant_ids.ids)
            bodies = self._render_field('body', res_ids=self.applicant_ids.ids)
        else:
            subjects = {applicant.id: self.subject for applicant in self.applicant_ids}
            bodies = {applicant.id: self.body for applicant in self.applicant_ids}

        for applicant in self.applicant_ids:
            if not applicant.partner_id:
                applicant.partner_id = self.env['res.partner'].create({
                    'is_company': False,
                    'name': applicant.partner_name,
                    'email': applicant.email_from,
                    'phone': applicant.partner_phone,
                })

            attachment_ids = []
            for attachment_id in self.attachment_ids:
                new_attachment = attachment_id.copy({'res_model': 'hr.applicant', 'res_id': applicant.id})
                attachment_ids.append(new_attachment.id)

            applicant.message_post(
                author_id=self.author_id.id,
                body=bodies[applicant.id],
                email_layout_xmlid='mail.mail_notification_light',
                message_type='comment',
                partner_ids=applicant.partner_id.ids,
                subject=subjects[applicant.id],
                attachment_ids=attachment_ids
            )
