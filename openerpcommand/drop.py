"""
Drop a database.
"""

import common

# TODO turn template1 in a parameter
# This should be exposed from openerp (currently in
# openerp/service/web_services.py).
def drop_database(database_name):
    import openerp
    db = openerp.sql_db.db_connect('template1')
    cr = db.cursor()
    cr.autocommit(True) # avoid transaction block
    try:
        # TODO option for doing this.
        # Try to terminate all other connections that might prevent
        # dropping the database
        try:
            cr.execute("""SELECT pg_terminate_backend(procpid)
                          FROM pg_stat_activity
                          WHERE datname = %s AND 
                                procpid != pg_backend_pid()""",
                       (database_name,))
        except Exception:
            pass

        try:
            cr.execute('DROP DATABASE "%s"' % database_name)
        except Exception, e:
            print "Can't drop %s" % (database_name,)
    finally:
        cr.close()

def run(args):
    assert args.database
    drop_database(args.database)

def add_parser(subparsers):
    parser = subparsers.add_parser('drop',
        description='Drop a database.')
    parser.add_argument('-d', '--database', metavar='DATABASE',
        **common.required_or_default('DATABASE', 'the database to create'))

    parser.set_defaults(run=run)
