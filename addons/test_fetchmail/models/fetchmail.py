from uuid import uuid4

from odoo import models
from odoo.modules.module import get_resource_path


class MockPOPServer(object):
    # A POP server which always return a single email in data/
    def __init__(self, *args, **kwargs):
        path = get_resource_path('test_fetchmail', 'data', 'malformed-email.txt')
        with open(path, 'rb') as fh:
            self.messages = [fh.read().format(message_id=str(uuid4()))]

    def stat(self):
        return 1, 13

    def retr(self, num):
        return ('header', self.messages, b'')

    def noop(self, *args, **kwargs):
        pass

    list = noop
    quit = noop
    dele = noop


class MockIMAPServer(object):
    # An IMAP server which always return a single email in data/
    def __init__(self, *args, **kwargs):
        path = get_resource_path('test_fetchmail', 'data', 'malformed-email.txt')
        with open(path, 'rb') as fh:
            self.message = fh.read().format(message_id=str(uuid4()))

    def search(self, *args):
        return 'typ', ['1\n']

    def fetch(self, *args):
        return b'envelop', [(13, self.message)]

    def noop(self, *args, **kwargs):
        pass

    select = noop
    store = noop
    close = noop
    logout = noop


class Fetchmail(models.Model):
    _inherit = 'fetchmail.server'

    def connect(self):
        if '__mock_me' in self.env.context:
            if self.type == 'imap':
                return MockIMAPServer()
            elif self.type == 'pop':
                return MockPOPServer()
            else:
                assert False
        else:
            return super(Fetchmail, self).connect()


class Message(models.Model):
    _inherit = 'mail.message'

    def create(self, values):
        if '__fail_message' in self.env.context:
            raise ValueError
        return super(Message, self).create(values)
