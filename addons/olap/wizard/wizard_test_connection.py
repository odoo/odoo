import psycopg2

import wizard
import pooler
import netsvc
from tools.misc import UpdateableStr, UpdateableDict


_connection_arch = UpdateableStr()

def _test_connection(self,cr,uid,part,context={}):
    lines=pooler.get_pool(cr.dbname).get('olap.fact.database').browse(cr, uid, part['id'],context)
    host = lines.db_host
    port = lines.db_port
    db_name = lines.db_name
    user = lines.db_login
    password = lines.db_password
    type = lines.type
    return_str = "Connection Successful"
    try:	
        if type == 'postgres':
            tdb = psycopg2.connect('host=%s port=%s dbname=%s user=%s password=%s' % (host, port, db_name, user, password))

        elif type == 'mysql':
            import MySQLdb
            tdb = MySQLdb.connect(host = host,port = port, db = db_name, user = user, passwd = password)
                

        elif type == 'oracle':
            import cx_Oracle
            tdb = cx_Oracle.connect(user, password, host)
                
    except Exception, e:
            return_str = e.message

    _arch = ['''<?xml version="1.0"?>''', '''<form string="Connection Status">''']
    _arch.append('''<label string='%s' />''' % (return_str))
    _arch.append('''</form>''')
    _connection_arch.string = '\n'.join(_arch)

    return {}



class wizard_test_connection(wizard.interface):
    states = {
        'init': {
            'actions': [_test_connection],
            'result': {'type':'form', 'arch': _connection_arch, 'fields':{}, 'state':[('end','Ok')]}
        },
    }
wizard_test_connection('olap.fact.database.test_connection')
