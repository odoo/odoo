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

# ------------------------------------------- #
# convert partner payment terms to properties #
# ------------------------------------------- #

# setup

cr.execute("select id from ir_model_fields where name='property_payment_term' and model='res.partner'")
fields_id = cr.fetchone()[0]

cr.execute("select company_id from res_users where company_id is not null limit 1")
company_id = cr.fetchone()[0]

# get partners
cr.execute("SELECT c.relname FROM pg_class c, pg_attribute a WHERE c.relname='res_partner' AND a.attname='payment_term' AND c.oid=a.attrelid")
partners=[]
drop_payment_term=False
if cr.rowcount:
    drop_payment_term=True
    cr.execute("select id, payment_term from res_partner where payment_term is not null")
    partners = cr.dictfetchall()

# loop over them

for partner in partners:
    value = 'account.payment.term,%d' % partner['payment_term']
    res_id = 'res.partner,%d' % partner['id']
    cr.execute(
        "insert into ir_property(name, value, res_id, company_id, fields_id) "\
        "values(%s, %s, %s, %d, %d)", 
        ('property_payment_term', value, res_id, company_id, fields_id))

# remove the field
if drop_payment_term:
    cr.execute("alter table res_partner drop column payment_term")
cr.execute("delete from ir_model_fields where model = 'res.partner' and name = 'payment_term'")

cr.commit()

# ------------------------ #
# remove duplicate reports #
# ------------------------ #

cr.execute("select model, report_name from ir_act_report_xml group by model, report_name having count(*)>1")
reports_wh_duplicates = cr.dictfetchall()

cr.execute("select res_id from ir_model_data where model='ir.actions.report.xml'")
registered_reports = cr.fetchall()
reg_reports_ids = ','.join([str(id) for (id,) in registered_reports])

for report in reports_wh_duplicates:
    cr.execute("select id from ir_act_report_xml where model=%s and report_name=%s and id not in ("+reg_reports_ids+")", (report['model'], report['report_name']))
    (id,) = cr.fetchone()
    cr.execute("delete from ir_act_report_xml where id=%d", (id,))
    cr.execute("delete from ir_values where value='ir.actions.report.xml,%d'", (id,))

cr.commit()

# ------------------------------------- #
# remove duplicate workflow transitions #
# ------------------------------------- #

# this removes all transitions which are not registered in ir_model_data

cr.execute("delete from wkf_transition where id not in (select res_id from ir_model_data where model='workflow.transition')")
cr.commit()

# -------------------------------- #
# remove bad "default" menu action #
# -------------------------------- #

cr.execute("delete from ir_values where key='action' and model='ir.ui.menu' and res_id is null")
cr.commit()

cr.close()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

