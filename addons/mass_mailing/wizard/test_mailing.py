# -*- coding: utf-8 -*-

from openerp import tools
from openerp.osv import osv, fields


class TestMassMailing(osv.TransientModel):
    _name = 'mail.mass_mailing.test'
    _description = 'Sample Mail Wizard'

    _columns = {
        'email_to': fields.char('Recipients', required=True,
            help='Comma-separated list of email addresses.'),
        'mass_mailing_id': fields.many2one('mail.mass_mailing', 'Mailing', required=True),
    }

    _defaults = {
        'email_to': lambda self, cr, uid, ctx=None: self.pool['mail.message']._get_default_from(cr, uid, context=ctx),
    }

    def send_mail_test(self, cr, uid, ids, context=None):
        Mail = self.pool['mail.mail']
        for wizard in self.browse(cr, uid, ids, context=context):
            mailing = wizard.mass_mailing_id
            test_emails = tools.email_split(wizard.email_to)
            mail_ids = []
            for test_mail in test_emails:
                # Convert links in absolute URLs before the application of the shortener
                self.pool['mail.mass_mailing'].write(cr, uid, [mailing.id], {'body_html': self.pool['mail.template']._replace_local_links(cr, uid, mailing.body_html, context)}, context=context)
                mail_values = {
                    'email_from': mailing.email_from,
                    'reply_to': mailing.reply_to,
                    'email_to': test_mail,
                    'subject': mailing.name,
                    'body_html': '',
                    'notification': True,
                    'mailing_id': mailing.id,
                    'attachment_ids': [(4, attachment.id) for attachment in mailing.attachment_ids],
                }
                mail_mail_obj = Mail.browse(cr, uid, Mail.create(cr, uid, mail_values, context=context), context=context)
                unsubscribe_url = Mail._get_unsubscribe_url(cr, uid, mail_mail_obj, test_mail, context=context)
                body = tools.append_content_to_html(mailing.body_html, unsubscribe_url, plaintext=False, container_tag='p')
                Mail.write(cr, uid, mail_mail_obj.id, {'body_html': mailing.body_html}, context=context)
                mail_ids.append(mail_mail_obj.id)
            Mail.send(cr, uid, mail_ids, context=context)
        return True
