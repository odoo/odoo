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

# ---------------------------------------------------------------- #
# move user id from hr_analytic_timesheet to account_analytic_line #
# ---------------------------------------------------------------- #

cr.execute("UPDATE account_analytic_line SET user_id = hr_analytic_timesheet.user_id FROM hr_analytic_timesheet WHERE hr_analytic_timesheet.line_id = account_analytic_line.id")
cr.commit()

# --------------- #
# remove old menu #
# --------------- #

while True:
    cr.execute("select id from ir_ui_menu where (id not in (select parent_id from ir_ui_menu where parent_id is not null)) and (id not in (select res_id from ir_values where model='ir.ui.menu'))")
    if not cr.rowcount:
        break
    cr.execute("delete from ir_ui_menu where (id not in (select parent_id from ir_ui_menu where parent_id is not null)) and (id not in (select res_id from ir_values where model='ir.ui.menu'))")
cr.commit()

# ----------------------------------------- #
# add default value for discount in invoice #
# ----------------------------------------- #

cr.execute("update account_invoice_line set discount=0.0 where discount is null;")
cr.commit()


# -------------------------------------------------------------------------- #
# update constraint account_invoice_line_uos_id_fkey on account_invoice_line #
# -------------------------------------------------------------------------- #

cr.execute("ALTER TABLE account_invoice_line DROP CONSTRAINT account_invoice_line_uos_id_fkey")
cr.execute("ALTER TABLE account_invoice_line ADD FOREIGN KEY (uos_id) REFERENCES product_uom(id) ON DELETE SET NULL")
cr.commit()

print """
WARNING: account_uos has been replaced by product_uom.
It is not possible to migrate the data automatically so you need to create the old account_uos in the new product_uom.
And then update the field uos_id of the table account_invoice to match the new id of product_uom.

EXAMPLE:
    UPDATE account_invoice SET uos_id = new_id WHERE uos_id = old_id;
"""

cr.close()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

