from markupsafe import Markup

from odoo import fields, models


class ShareWizard(models.TransientModel):
    _name = 'social.share.url.share.multi'

    share_campaign_id = fields.Many2one('social.share.campaign', string='Social Share Campaign', ondelete='cascade', require=True)
    domain = fields.Char(default="[]")
    message = fields.Html()
    model = fields.Char(related='share_campaign_id.model_id.model')

    def action_send(self):
        composer = self.env['mail.compose.message'].create({
            'composition_mode': 'mass_mail',
            'force_default_recipients': True,
            'model': self.model,
            'res_domain': self.domain or '[]',
            'template_id': self.share_campaign_id.mail_template_id.id,
        })
        # TODO test this
        composer.body = composer.body.replace(Markup('<div id="message"></div>'), Markup(f'<div id="message">{self.message}</div>'))
        composer._action_send_mail()
        return {'type': 'ir.actions.act_window_close'}


class MailComposer(models.TransientModel):
    """Override of mail composer to be able to send templates without specified recipients."""
    _inherit = 'mail.compose.message'

    force_default_recipients = fields.Boolean()

    def _prepare_mail_values_dynamic(self, res_ids):
        """Set default recipient if no other, as the template won't have one by default."""
        # TODO test this
        mail_values = super()._prepare_mail_values_dynamic(res_ids)
        if not self.force_default_recipients:
            return mail_values
        default_recipients = self.env[self.model].browse(res_ids)._message_get_default_recipients()
        for res_id in res_ids:
            if not mail_values[res_id].get('partner_id') and not mail_values[res_id].get('email_to'):
                mail_values[res_id].update(default_recipients[res_id])
        return mail_values
