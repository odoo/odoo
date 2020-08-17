from odoo.addons.test_mail.data import test_mail_data
from odoo.addons.test_mail.tests.common import TestMailCommon
import odoo.tools
import difflib
import re


def unix2dos(text):
    """
    Replace \n ended lines by \r\n

    >>> unix2dos("abc\nde\r\nfg\n\n\nh") == "abc\r\nde\r\nfh\r\n\r\n\r\nh"
    """
    return re.sub(r'([^\r])\n', r'\1\r\n', re.sub(r'\n\n', '\r\n\r\n', text))


unix = "Hello\nWorld\r\nSome\n\n\nText"
dos = unix2dos(unix)
assert dos == "Hello\r\nWorld\r\nSome\r\n\r\n\r\nText", dos.encode()



class TestMailCycle(TestMailCommon):
    def test_mail_cycle(self):
        kwargs = {
            'email_from': 'Jordi Mcmanus <jordi@example.com>',
            'to': 'Marco <marco@example.com>, Kaleb <kaleb@example.com>',
            'cc': 'Torin Rennie <torin@example.com>',
            'msg_id': odoo.tools.generate_tracking_message_id(0xBEEF),
            'subject': "It's very hot out there",
            'extra': ''
        }

        with self.mock_mail_gateway():
            for template in filter(str.isupper, dir(test_mail_data)):
                in_message_str = unix2dos(getattr(test_mail_data, template)).format(**kwargs)
                in_message = self.from_string(in_message_str)
                self.env['ir.mail_server'].send_email(in_message)
                out_message_str = self._mails_str.pop()

                # Only compute diff when necessary
                if in_message_str == out_message_str:
                    continue

                diff = "\n".join(difflib.ndiff(
                    in_message_str.split('\r\n'),
                    out_message_str.split('\r\n'),
                ))
                raise AssertionError(
                    ("Template email {} is different when regenerated. "
                     "Line diff bellow, [-] Template, [+] Output.\n{}"
                    ).format(template, diff)
                )
                        
