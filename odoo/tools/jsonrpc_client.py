# Part of Odoo. See LICENSE file for full copyright and licensing details.

import functools
import uuid
import requests as requests_
from urllib.parse import quote


def call(
    method, *params, scheme, domain, database=None, username=None,
    password=None, requests=requests_
):
    """
    Execute a single procedure on the remote server via JSON-RPC.

    See also ``odoo.utils.jsonrpc.proxy`` to execute multiple procedures
    on a same remote server.

    .. warning

       JSON-RPC doesn't support binary data but XML-RPC does, see
       ``xmlrpc.client.Server``.

    >>> call('res.partner.search_read', {
             'records': [1, 2],
             'context': {'lang': 'en_US'},
             'args': [['id', 'name']],
             'kwargs': {'load': None}
        },
        scheme='https',
        domain='mycompany.odoo.com',
        database='mycompany',
        username='admin',
        password='admin'
    )
    [{'id': 1, 'name': 'Bob'}, {'id': 2, 'name': 'Eve'}]

    :param str method: the remote procedure that will be executed
    :param Sequence params: the args to call the remote procedure with
    :param str scheme: the network scheme of the underlying connection
    :param str domain: the domain name and port where to connect to
    :param str|None database: the odoo database to connect to
    :param str|None username: the username for the authentication
    :param str|None password: the password for the authentication
    :param requests: An opener from the ``requests`` library, by default
        it is ``requests`` itself.
    """
    should_auth = username is not None or password is not None
    url = f'{scheme}://{domain}/RPC2'
    if database:
        url += f'?db={quote(database)}'

    res = requests.post(
        url,
        json={
            'jsonrpc': '2.0',
            'method': method,
            'params': params,
            'id': str(uuid.uuid4()),
        },
        **{'auth': (username, password) for _ in (1,) if should_auth},
    )
    res.raise_for_status()
    res_data = res.json()
    if 'error' in res_data:
        raise Exception(res_data['error']['message'])
    return res_data['result']


class _Method:
    def __init__(self, callback, attrs):
        self.callback = callback
        self._attrs = attrs

    def __getattr__(self, attr):
        return type(self)(self.callback, (*self._attrs, attr))

    def __call__(self, *args):
        return self.callback('.'.join(self._attrs), *args)

def proxy(scheme, domain, database=None, username=None, password=None, requests=requests_):
    """
    Create a JSON-RPC proxy to a remote server.

    See also ``xmlrpc.client.ServerProxy`` which has support for binary
    data that JSON-RPC lacks.

    >>> common = proxy('https', 'mycompany.odoo.com')
    >>> common.version()
    >>> {'server_version': '16.0', ...}

    >>> models = proxy('https', 'mycompany.odoo.com', 'mycompany', 'admin', 'admin')
    >>> models.res.partner.read({
            'records': [1, 2],
            'context': {'lang': 'en_US'},
            'args': [['id', 'name']],
            'kwargs': {'load': None},
        })
    [{'id': 1, 'name': 'Bob'}, {'id': 2, 'name': 'Eve'}]

    :param str scheme: the network scheme of the underlying connection
    :param str domain: the domain name where the Odoo server is at
    :param str|None database: the optional database to log on
    :param str|None username: the username for the authentication
    :param str|None password: the password for the authentication
    :param requests: An opener from the ``requests`` library, by default
        it is ``requests`` itself.
    """
    callback = functools.partial(call,
        scheme=scheme, domain=domain, database=database, username=username,
        password=password, requests=requests
    )
    return _Method(callback, tuple())
