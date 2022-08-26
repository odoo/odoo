import threading

from werkzeug.urls import URL

import odoo

HOST = '127.0.0.1'


def base_url() -> URL:
    return URL('http', f"{HOST}:{odoo.tools.config['http_port']}", '', '', '')


def get_db_name():
    db = odoo.tools.config['db_name']
    # If the database name is not provided on the command-line,
    # use the one on the thread (which means if it is provided on
    # the command-line, this will break when installing another
    # database from XML-RPC).
    if not db and hasattr(threading.current_thread(), 'dbname'):
        return threading.current_thread().dbname
    return db
