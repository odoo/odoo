from odoo.tests import SavepointCase
from unittest import mock
import smtplib


class MailCase(SavepointCase):

    def test_mail_send_missing_not_connected(self):
        """This assume while calling self.env['ir.mail_server'].connect() it return
        an disconnected smtp_session which is a non falsy object value"""
        
        not_connected = smtplib.SMTP(local_hostname="fake-hostname.com", port=9999, timeout=1)
        mail = self.env["mail.mail"].new({})
        with mock.patch("odoo.addons.base.models.ir_mail_server.IrMailServer.connect", return_value=not_connected):
            mail.send()
        # if we get here SMTPServerDisconnected was not raised
        self.assertEqual(mail.state, "outgoing")