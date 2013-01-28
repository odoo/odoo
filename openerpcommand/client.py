"""
Define a few common arguments for client-side command-line tools.
"""
import os
import sys
import time
import xmlrpclib

import common

class Client(common.Command):
    """
    Base class for XML-RPC command-line clients. It must be inherited and the
    work() method overriden.
    """

    def __init__(self, subparsers=None):
        super(Client, self).__init__(subparsers)
        required_or_default = common.required_or_default
        self.parser.add_argument('-H', '--host', metavar='HOST',
            **required_or_default('HOST', 'the server host'))
        self.parser.add_argument('-P', '--port', metavar='PORT',
            **required_or_default('PORT', 'the server port'))

    def execute(self, *args):
        return self.object_proxy.execute(self.database, self.uid, self.password, *args)

    def initialize(self):
        self.host = self.args.host
        self.port = int(self.args.port)
        self.database = self.args.database
        self.user = self.args.user
        self.password = self.args.password

        self.url = 'http://%s:%d/xmlrpc/' % (self.host, self.port)
        self.common_proxy = xmlrpclib.ServerProxy(self.url + 'common')
        self.object_proxy = xmlrpclib.ServerProxy(self.url + 'object')

        try:
            self.uid = int(self.user)
        except ValueError, e:
            self.uid = self.common_proxy.login(self.database, self.user, self.password)

    def run(self, *args):
        self.initialize()
        self.work(*args)

    def work(self, *args):
        pass

class Open(Client):
    """Get the web client's URL to view a specific model."""

    command_name = 'open'

    def __init__(self, subparsers=None):
        super(Open, self).__init__(subparsers)
        self.parser.add_argument('-m', '--model', metavar='MODEL',
            required=True, help='the view type')
        self.parser.add_argument('-v', '--view-mode', metavar='VIEWMODE',
            default='tree', help='the view mode')

    def work(self):
        ids = self.execute('ir.actions.act_window', 'search', [
            ('res_model', '=', self.args.model),
            ('view_mode', 'like', self.args.view_mode),
            ])
        xs = self.execute('ir.actions.act_window', 'read', ids, [])
        for x in xs:
            print x['id'], x['name']
            d = {}
            d['host'] = self.host
            d['port'] = self.port
            d['action_id'] = x['id']
            print "  http://%(host)s:%(port)s/web/webclient/home#action_id=%(action_id)s" % d

class Show(Client):
    """Display a record."""

    command_name = 'show'

    def __init__(self, subparsers=None):
        super(Show, self).__init__(subparsers)
        self.parser.add_argument('-m', '--model', metavar='MODEL',
            required=True, help='the model')
        self.parser.add_argument('-i', '--id', metavar='RECORDID',
            required=True, help='the record id')

    def work(self):
        xs = self.execute(self.args.model, 'read', [self.args.id], [])
        if xs:
            x = xs[0]
            print x['name']
        else:
            print "Record not found."

class ConsumeNothing(Client):
    """Call test.limits.model.consume_nothing()."""

    command_name = 'consume-nothing'

    def work(self):
        xs = self.execute('test.limits.model', 'consume_nothing')

class ConsumeMemory(Client):
    """Call test.limits.model.consume_memory()."""

    command_name = 'consume-memory'

    def __init__(self, subparsers=None):
        super(ConsumeMemory, self).__init__(subparsers)
        self.parser.add_argument('--size', metavar='SIZE',
            required=True, help='size of the list to allocate')

    def work(self):
        xs = self.execute('test.limits.model', 'consume_memory', int(self.args.size))

class LeakMemory(ConsumeMemory):
    """Call test.limits.model.leak_memory()."""

    command_name = 'leak-memory'

    def work(self):
        xs = self.execute('test.limits.model', 'leak_memory', int(self.args.size))

class ConsumeCPU(Client):
    """Call test.limits.model.consume_cpu_time()."""

    command_name = 'consume-cpu'

    def __init__(self, subparsers=None):
        super(ConsumeCPU, self).__init__(subparsers)
        self.parser.add_argument('--seconds', metavar='INT',
            required=True, help='how much CPU time to consume')

    def work(self):
        xs = self.execute('test.limits.model', 'consume_cpu_time', int(self.args.seconds))
