# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.     
#
##############################################################################

__author__ = 'Gaetan de Menten, <ged@tiny.be>'
__version__ = '0.1.0'

import psycopg
import optparse
import ConfigParser

# -----

parser = optparse.OptionParser(version="Tiny ERP server migration script " + __version__)

parser.add_option("-c", "--config", dest="config", help="specify path to Tiny ERP config file")

group = optparse.OptionGroup(parser, "Database related options")
group.add_option("--db_host", dest="db_host", help="specify the database host") 
group.add_option("--db_port", dest="db_port", help="specify the database port") 
group.add_option("-d", "--database", dest="db_name", help="specify the database name")
group.add_option("-r", "--db_user", dest="db_user", help="specify the database user name")
group.add_option("-w", "--db_password", dest="db_password", help="specify the database password") 
parser.add_option_group(group)

options = optparse.Values()
options.db_name = 'terp' # default value
parser.parse_args(values=options)

if hasattr(options, 'config'):
    configparser = ConfigParser.ConfigParser()
    configparser.read([options.config])
    for name, value in configparser.items('options'):
        if not (hasattr(options, name) and getattr(options, name)):
            if value in ('true', 'True'):
                value = True
            if value in ('false', 'False'):
                value = False
            setattr(options, name, value)

# -----

host = hasattr(options, 'db_host') and "host=%s" % options.db_host or ''
port = hasattr(options, 'db_port') and "port=%s" % options.db_port or ''
name = "dbname=%s" % options.db_name
user = hasattr(options, 'db_user') and "user=%s" % options.db_user or ''
password = hasattr(options, 'db_password') and "password=%s" % options.db_password or ''

db = psycopg.connect('%s %s %s %s %s' % (host, port, name, user, password), serialize=0)
cr = db.cursor()

# ------------------------- #
# change some columns types #
# ------------------------- #

def change_column(cr, table, column, new_type, copy):
    commands = [
        "ALTER TABLE %s RENAME COLUMN %s TO temp_column" % (table, column),
        "ALTER TABLE %s ADD COLUMN %s %s" % (table, column, new_type),
        "ALTER TABLE %s DROP COLUMN temp_column" % table
    ]
    if copy:
        commands.insert(
            2, 
            "UPDATE %s SET %s=temp_column::%s" % (table, column, new_type))

    for command in commands:
        cr.execute(command)

change_column(cr, 'account_account_type', 'code_from', 'varchar(10)', False)
change_column(cr, 'account_account_type', 'code_to', 'varchar(10)', False)
cr.commit()

# ----------------------------------------------------- #
# add some fields (which cannot be added automatically) #
# ----------------------------------------------------- #

for line in (
        "alter table ir_model_fields add group_name varchar(64)",
        "alter table ir_model_fields add view_load boolean",
        "alter table ir_model_fields alter group_name set default ''",
        "alter table ir_model_fields alter view_load set default False",
        "delete from ir_values where value like '%,False'",
    ):
    try:
        cr.execute(line)
    except psycopg.ProgrammingError, e:
        cr.commit()
        print e

cr.commit()
cr.close()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

