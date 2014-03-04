import urllib
import urlparse
from openerp import sql_db, tools
from qunitsuite.suite import QUnitSuite

class WebSuite(QUnitSuite):
    def __init__(self, module):
        url = urlparse.urlunsplit([
            'http',
            'localhost:{port}'.format(port=tools.config['xmlrpc_port']),
            '/web/tests',
            urllib.urlencode({
                'mod': module,
                'source': tools.config['db_name'],
                'supadmin': tools.config['admin_passwd'],
                'password': 'admin',
            }),
            ''
        ])
        super(WebSuite, self).__init__(url, 50000)

def load_tests(loader, standard_tests, _):
    standard_tests.addTest(WebSuite('web'))
    return standard_tests
