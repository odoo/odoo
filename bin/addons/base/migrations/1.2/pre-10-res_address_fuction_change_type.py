# -*- coding: utf8 -*-

__name__ = "res.partner.address: change type of 'function' field many2one to char"

def migrate(cr, version):
    change_column_type(cr,'res_partner_address')

def change_column_type(cr,table):
    cr.execute('SELECT id, name FROM res_partner_function')
    all_function = cr.fetchall()
    cr.execute('ALTER TABLE %s ADD COLUMN temp_function VARCHAR(64)' % table)
    for fn in all_function:
        cr.execute("UPDATE %s SET temp_function = '%s' WHERE function = %s" % (table,fn[1],fn[0]))
    cr.execute("ALTER TABLE %s DROP COLUMN function CASCADE" % table)
    cr.execute("ALTER TABLE %s RENAME COLUMN temp_function TO function" % table)

