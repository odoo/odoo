from odoo import _, api, exceptions, models


class MailTemplate(models.Model):
    _inherit = 'mail.template'

    @api.ondelete(at_uninstall=False)
    def _unlink_except_appraisal_request_templates(self):
        templates = self.env.ref("hr_appraisal.mail_template_appraisal_request", raise_if_not_found=False) or self.env['mail.template']
        templates += self.env.ref("hr_appraisal.mail_template_appraisal_request_from_employee", raise_if_not_found=False) or self.env['mail.template']
        if unlinked_templates := templates & self:
            raise exceptions.ValidationError(_(
                "Template %(template_name)s is necessary for appraisal requests and may not be removed.",
                template_name=unlinked_templates[0].display_name
            ))
