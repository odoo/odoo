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
                mail_values = {
                    'email_from': mailing.email_from,
                    'reply_to': mailing.reply_to,
                    'email_to': test_mail,
                    'subject': mailing.name,
                    'body_html': mailing.body_html,
                    'auto_delete': True,
                    'mailing_id': wizard.mass_mailing_id.id,
                }
                mail_ids.append(Mail.create(cr, uid, mail_values, context=context))
            Mail.send(cr, uid, mail_ids, context=context)
            self.pool['mail.mass_mailing'].write(cr, uid, [mailing.id], {'state': 'test'}, context=context)
        return True
