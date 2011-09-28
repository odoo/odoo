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

__author__ = 'Cédric Krier, <ced@tinyerp.com>'
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

raise Exception('This script is provided as an example, you must custom it before')

# -----

host = hasattr(options, 'db_host') and "host=%s" % options.db_host or ''
port = hasattr(options, 'db_port') and "port=%s" % options.db_port or ''
name = "dbname=%s" % options.db_name
user = hasattr(options, 'db_user') and "user=%s" % options.db_user or ''
password = hasattr(options, 'db_password') and "password=%s" % options.db_password or ''

db = psycopg.connect('%s %s %s %s %s' % (host, port, name, user, password), serialize=0)
cr = db.cursor()

# fix country


cr.execute('SELECT code from res_country where code is not null group by code')
res = cr.fetchall()

for c in res:
    cr.execute('SELECT max(id) from res_country where code = %s group by code', (c[0],))
    res2 = cr.fetchone()
    cr.execute('SELECT id from res_country where code = %s', (c[0],))
    ids = ','.join(map(lambda x: str(x[0]), cr.fetchall()))
    cr.execute('UPDATE res_partner_address set country_id = %d where country_id in ('+ids+')', (res2[0],))
    cr.execute('DELETE FROM res_country WHERE code = %s and id <> %d', (c[0], res2[0],))
cr.commit()


cr.execute('SELECT viewname FROM pg_views WHERE viewname = \'report_account_analytic_planning_stat\'')
if cr.fetchall():
    cr.execute('DROP VIEW report_account_analytic_planning_stat')
cr.commit()


cr.execute('SELECT name from ( SELECT name, count(name) AS n FROM res_partner GROUP BY name ) AS foo WHERE n > 1')
res = cr.fetchall()


for p in res:
    cr.execute('SELECT max(id) FROM res_partner WHERE name = %s GROUP BY name', (p[0],))
    res2 = cr.fetchone()
    cr.execute('UPDATE res_partner set active = False WHERE name = %s and id <> %d', (p[0], res2[0],))
    cr.execute('SELECT id FROM res_partner WHERE name = %s AND id <> %d', (p[0], res2[0],))
    res3 = cr.fetchall()
    i = 0
    for id in res3:
        name = p[0]+' old'
        if i:
            name = name + ' ' + str(i)
        cr.execute('UPDATE res_partner set name = %s WHERE id = %d', (name, id[0]))
        i += 1
cr.commit()

cr.execute('SELECT viewname FROM pg_views WHERE viewname = \'report_account_analytic_line_to_invoice\'')
if cr.fetchall():
    cr.execute('DROP VIEW report_account_analytic_line_to_invoice')
cr.execute('SELECT viewname FROM pg_views WHERE viewname = \'report_timesheet_invoice\'')
if cr.fetchall():
    cr.execute('drop VIEW report_timesheet_invoice')
cr.execute('SELECT viewname FROM pg_views WHERE viewname = \'report_purchase_order_category\'')
if cr.fetchall():
    cr.execute('drop VIEW report_purchase_order_category')
cr.execute('SELECT viewname FROM pg_views WHERE viewname = \'report_purchase_order_product\'')
if cr.fetchall():
    cr.execute('drop VIEW report_purchase_order_product')
cr.execute('SELECT viewname FROM pg_views WHERE viewname = \'report_sale_order_category\'')
if cr.fetchall():
    cr.execute('drop VIEW report_sale_order_category')
cr.execute('SELECT viewname FROM pg_views WHERE viewname = \'report_sale_order_product\'')
if cr.fetchall():
    cr.execute('drop VIEW report_sale_order_product')
cr.execute('SELECT viewname FROM pg_views WHERE viewname = \'report_timesheet_user\'')
if cr.fetchall():
    cr.execute('drop VIEW report_timesheet_user')
cr.execute('SELECT viewname FROM pg_views WHERE viewname = \'report_task_user_pipeline_open\'')
if cr.fetchall():
    cr.execute('drop VIEW report_task_user_pipeline_open')
cr.execute('SELECT viewname FROM pg_views WHERE viewname = \'hr_timesheet_sheet_sheet_day\'')
if cr.fetchall():
    cr.execute('drop VIEW hr_timesheet_sheet_sheet_day')
cr.execute('SELECT viewname FROM pg_views WHERE viewname = \'hr_timesheet_sheet_sheet_account\'')
if cr.fetchall():
    cr.execute('drop VIEW hr_timesheet_sheet_sheet_account')
cr.execute('SELECT viewname from pg_views where viewname = \'sale_journal_sale_stats\'')
if cr.fetchall():
    cr.execute('drop VIEW sale_journal_sale_stats')
cr.execute('SELECT viewname from pg_views where viewname = \'sale_journal_picking_stats\'')
if cr.fetchall():
    cr.execute('drop VIEW sale_journal_picking_stats')
cr.execute('SELECT viewname from pg_views where viewname = \'sale_journal_invoice_type_stats\'')
if cr.fetchall():
    cr.execute('drop VIEW sale_journal_invoice_type_stats')

cr.execute('ALTER TABLE product_template ALTER list_price TYPE numeric(16,2)')
cr.execute('ALTER TABLE product_template ALTER standard_price TYPE numeric(16,2)')
cr.execute('ALTER TABLE product_product ALTER price_extra TYPE numeric(16,2)')
cr.execute('ALTER TABLE product_product ALTER price_margin TYPE numeric(16,2)')
cr.execute('ALTER TABLE pricelist_partnerinfo ALTER price TYPE numeric(16,2)')
cr.execute('ALTER TABLE account_invoice_line ALTER price_unit TYPE numeric(16,2)')
cr.execute('ALTER TABLE purchase_order_line ALTER price_unit TYPE numeric(16,2)')
cr.execute('ALTER TABLE sale_order_line ALTER price_unit TYPE numeric(16,2)')
cr.commit()


cr.execute('SELECT tablename FROM pg_tables WHERE tablename = \'subscription_document_fields\'')
if cr.fetchall():
    cr.execute('DROP TABLE subscription_document_fields')
cr.execute('SELECT tablename FROM pg_tables WHERE tablename = \'subscription_document\'')
if cr.fetchall():
    cr.execute('DROP TABLE subscription_document')
cr.execute('SELECT tablename FROM pg_tables WHERE tablename = \'subscription_subscription_history\'')
if cr.fetchall():
    cr.execute('DROP TABLE subscription_subscription_history')
cr.commit()

# -------------------- #
# Change currency rate #
# -------------------- #

cr.execute('SELECT a.attname FROM pg_class c, pg_attribute a WHERE c.relname = \'res_currency_rate\' AND a.attname = \'rate_old\' AND c.oid = a.attrelid')
if not cr.fetchall():
    cr.execute('ALTER TABLE res_currency_rate ADD rate_old NUMERIC(12,6)')
    cr.execute('UPDATE res_currency_rate SET rate_old = rate')
    cr.execute('UPDATE res_currency_rate SET rate = (1 / rate_old)')
cr.commit()

cr.close

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

