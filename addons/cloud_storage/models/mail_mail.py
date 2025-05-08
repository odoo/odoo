# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import models, tools


class MailMail(models.Model):
    """Add the mass mailing campaign data to mail"""
    _inherit = ['mail.mail']

    def _prepare_outgoing_list(self, mail_server=False, recipients_follower_status=None):
        outgoing_list = super()._prepare_outgoing_list(
            mail_server=mail_server,
            recipients_follower_status=recipients_follower_status
        )

        # Turn remaining attachments into links appended to an email if they are cloud attachments
        for mail, outgoing in zip(self, outgoing_list):
            cloud_attachments = mail.attachment_ids.filtered(
                lambda attachment: attachment.type == 'cloud_storage'
                    and attachment.res_model != 'mail.message'
                    and attachment.res_id
            )
            if not cloud_attachments:
                continue

            # Prevent double-linking in the case that user already link to the attachment in the email
            link_ids = {int(link) for link in re.findall(r'/web/(?:content|image)/([0-9]+)', outgoing['body'])}
            if link_ids:
                cloud_attachments -= self.env['ir.attachment'].browse(list(link_ids))

            cloud_attachments.sudo().generate_access_token()
            cloud_links = self.env['ir.qweb']._render('mail.mail_attachment_links', {'attachments': cloud_attachments})
            updated_body = tools.mail.append_content_to_html(outgoing['body'], cloud_links, plaintext=False)

            outgoing['body'] = updated_body
            outgoing['body_alternative'] = tools.html2plaintext(updated_body)

            # Remove cloud attachments from outgoing
            remaining_attachments = mail.attachment_ids - cloud_attachments
            email_attachments = [
                (a['name'], a['raw'], a['mimetype'])
                for a in remaining_attachments.sudo().read(['name', 'raw', 'mimetype'])
                if a['raw'] is not False
            ]
            outgoing['attachments'] = email_attachments

        return outgoing_list
