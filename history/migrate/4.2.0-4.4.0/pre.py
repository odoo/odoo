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

# ------------------------------ #
# drop not null on ir_attachment #
# ------------------------------ #

cr.execute('ALTER TABLE ir_attachment \
        ALTER COLUMN res_model DROP NOT NULL, \
        ALTER COLUMN res_id DROP NOT NULL')
cr.commit()

# ---------------------------------- #
# change case date_deadline rounding #
# ---------------------------------- #

cr.execute("""SELECT
c.relname,a.attname,a.attlen,a.atttypmod,a.attnotnull,a.atthasdef,t.typname,CASE
WHEN a.attlen=-1 THEN a.atttypmod-4 ELSE a.attlen END as size FROM pg_class
c,pg_attribute a,pg_type t WHERE c.relname='crm_case' AND
a.attname='date_deadline' AND c.oid=a.attrelid AND a.atttypid=t.oid""")

res = cr.dictfetchall()
if res[0]['typname'] != 'timestamp':
    for line in (
        "ALTER TABLE crm_case RENAME date_deadline TO date_deadline_bak",
        "ALTER TABLE crm_case ADD date_deadline timestamp",
        "UPDATE crm_case SET date_deadline = date_deadline_bak",
        "ALTER TABLE crm_case DROP date_deadline_bak",
        ):
        cr.execute(line)
cr.commit()

cr.execute('drop view report_task_user_pipeline_open');
cr.commit()

cr.execute('alter table ir_model_fields add state varchar(26)')
cr.execute('alter table ir_model_fields add select_level varchar(3)')
cr.execute('alter table ir_act_wizard add primary key(id)')
cr.commit()


cr.close()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

