import urlparse
from openerp import sql_db, tools
from qunitsuite.suite import QUnitSuite

class WebSuite(QUnitSuite):
    def __init__(self):
        url = urlparse.urlunsplit([
            'http',
            'localhost:{port}'.format(port=tools.config['xmlrpc_port']),
            '/web/tests',
            'mod=*&source={db}&supadmin={supadmin}&password={password}'.format(
                db=tools.config['db_name'],
                # al: i dont understand why both are needed, db_password is the
                # password for postgres and should not appear here of that i'm
                # sure
                #
                # But runbot provides it with this wrong key so i let it here
                # until it's fixed
                supadmin=tools.config['db_password'] or 'admin',
                password=tools.config['admin_passwd'] or 'admin'),
            ''
        ])
        super(WebSuite, self).__init__(url, 50000)
    def run(self, result):
        if sql_db._Pool is not None:
            sql_db._Pool.close_all(sql_db.dsn(tools.config['db_name']))
        return super(WebSuite, self).run(result)

def load_tests(loader, standard_tests, _):
    standard_tests.addTest(WebSuite())
    return standard_tests
