# -*- coding: utf-8 -*-

from openerp import tools
from openerp.osv import osv, fields


class TestMassMailing(osv.TransientModel):
    _name = 'mail.mass_mailing.test'
    _description = 'Tets Mailing Wizard'

    _columns = {
        'email_to': fields.char(
            'Emails', required=True,
            help='Comma-separated list of email addresses.'),
        'mass_mailing_id': fields.many2one('mail.mass_mailing', 'Mailing', required=True),
    }

    def send_mail_test(self, cr, uid, ids, context=None):
        Mail = self.pool['mail.mail']
        for wizard in self.browse(cr, uid, ids, context=context):
            mailing = wizard.mass_mailing_id
            if not mailing.template_id:
                raise Warning('Please specify on your mailing the template to use.')
            test_emails = tools.email_split(wizard.email_to)
            if not test_emails:
                raise Warning('Please specify test email adresses.')
            mail_ids = []
            for test_mail in test_emails:
                body = mailing.template_id.body_html
                unsubscribe_url = self.pool['mail.mass_mailing'].get_unsubscribe_url(cr, uid, mailing.id, 0, email=test_mail, context=context)
                body = tools.append_content_to_html(body, unsubscribe_url, plaintext=False, container_tag='p')
                mail_values = {
                    'email_from': mailing.email_from,
                    'reply_to': mailing.reply_to,
                    'email_to': test_mail,
                    'subject': mailing.name,
                    'body_html': body,
                    'auto_delete': True,
                }
                mail_ids.append(Mail.create(cr, uid, mail_values, context=context))
            Mail.send(cr, uid, mail_ids, context=context)
            self.pool['mail.mass_mailing'].write(cr, uid, [mailing.id], {'state': 'test'}, context=context)
        return True
