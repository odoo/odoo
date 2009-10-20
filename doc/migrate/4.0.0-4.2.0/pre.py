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

# -----

host = hasattr(options, 'db_host') and "host=%s" % options.db_host or ''
port = hasattr(options, 'db_port') and "port=%s" % options.db_port or ''
name = "dbname=%s" % options.db_name
user = hasattr(options, 'db_user') and "user=%s" % options.db_user or ''
password = hasattr(options, 'db_password') and "password=%s" % options.db_password or ''

db = psycopg.connect('%s %s %s %s %s' % (host, port, name, user, password), serialize=0)
cr = db.cursor()

# ------------------------ #
# change currency rounding #
# ------------------------ #

cr.execute("""SELECT c.relname,a.attname,a.attlen,a.atttypmod,a.attnotnull,a.atthasdef,t.typname,CASE WHEN a.attlen=-1 THEN a.atttypmod-4 ELSE a.attlen END as size FROM pg_class c,pg_attribute a,pg_type t WHERE c.relname='res_currency' AND a.attname='rounding' AND c.oid=a.attrelid AND a.atttypid=t.oid""")
res = cr.dictfetchall()
if res[0]['typname'] != 'numeric':
    for line in (
        "ALTER TABLE res_currency RENAME rounding TO rounding_bak",
        "ALTER TABLE res_currency ADD rounding NUMERIC(12,6)",
        "UPDATE res_currency SET rounding = power(10, - rounding_bak)",
        "ALTER TABLE res_currency DROP rounding_bak",
        ):
        cr.execute(line)
cr.commit()

# ----------------------------- #
# drop constraint on ir_ui_view #
# ----------------------------- #

cr.execute('SELECT conname FROM pg_constraint where conname = \'ir_ui_view_type\'')
if cr.fetchall():
    cr.execute('ALTER TABLE ir_ui_view DROP CONSTRAINT ir_ui_view_type')
cr.commit()

# ------------------------ #
# update res.partner.bank  #
# ------------------------ #

cr.execute('SELECT a.attname FROM pg_class c, pg_attribute a WHERE c.relname = \'res_partner_bank\' AND a.attname = \'iban\' AND c.oid = a.attrelid')
if cr.fetchall():
    cr.execute('ALTER TABLE res_partner_bank RENAME iban TO acc_number')
cr.commit()

# ------------------------------------------- #
# Add perm_id to ir_model and ir_model_fields #
# ------------------------------------------- #

cr.execute('SELECT a.attname FROM pg_class c, pg_attribute a WHERE c.relname = \'ir_model\' AND a.attname = \'perm_id\' AND c.oid = a.attrelid')
if not cr.fetchall():
    cr.execute("ALTER TABLE ir_model ADD perm_id int references perm on delete set null")
cr.commit()

cr.execute('SELECT a.attname FROM pg_class c, pg_attribute a WHERE c.relname = \'ir_model_fields\' AND a.attname = \'perm_id\' AND c.oid = a.attrelid')
if not cr.fetchall():
    cr.execute("ALTER TABLE ir_model_fields ADD perm_id int references perm on delete set null")
cr.commit()


# --------------------------------- #
# remove name for all ir_act_window #
# --------------------------------- #

cr.execute("UPDATE ir_act_window SET name = ''")
cr.commit()

# ------------------------------------------------------------------------ #
# Create a "allow none" default access to keep the behaviour of the system #
# ------------------------------------------------------------------------ #

cr.execute('SELECT model_id FROM ir_model_access')
res= cr.fetchall()
for r in res:
    cr.execute('SELECT id FROM ir_model_access WHERE model_id = %d AND group_id IS NULL', (r[0],))
    if not cr.fetchall():
        cr.execute("INSERT into ir_model_access (name,model_id,group_id) VALUES ('Auto-generated access by migration',%d,NULL)",(r[0],))
cr.commit()

# ------------------------------------------------- #
# Drop view report_account_analytic_line_to_invoice #
# ------------------------------------------------- #

cr.execute('SELECT viewname FROM pg_views WHERE viewname = \'report_account_analytic_line_to_invoice\'')
if cr.fetchall():
    cr.execute('DROP VIEW report_account_analytic_line_to_invoice')
cr.commit()

# --------------------------- #
# Drop state from hr_employee #
# --------------------------- #

cr.execute('SELECT * FROM pg_class c, pg_attribute a WHERE c.relname=\'hr_employee\' AND a.attname=\'state\' AND c.oid=a.attrelid')
if cr.fetchall():
    cr.execute('ALTER TABLE hr_employee DROP state')
cr.commit()

# ------------ #
# Add timezone #
# ------------ #

cr.execute('SELECT id FROM ir_values where model=\'res.users\' AND key=\'meta\' AND name=\'tz\'')
if not cr.fetchall():
    import pytz, pickle
    meta = pickle.dumps({'type':'selection', 'string':'Timezone', 'selection': [(x, x) for x in pytz.all_timezones]})
    value = pickle.dumps(False)
    cr.execute('INSERT INTO ir_values (name, key, model, meta, key2, object, value) VALUES (\'tz\', \'meta\', \'res.users\', %s, \'tz\', %s, %s)', (meta,False, value))
cr.commit()

# ------------------------- #
# change product_uom factor #
# ------------------------- #

cr.execute('SELECT a.attname FROM pg_class c, pg_attribute a, pg_type t WHERE c.relname = \'product_uom\' AND a.attname = \'factor\' AND c.oid = a.attrelid AND a.atttypid = t.oid AND t.typname = \'float8\'')
if cr.fetchall():
    cr.execute('SELECT viewname FROM pg_views WHERE viewname = \'report_account_analytic_planning_stat_account\'')
    if cr.fetchall():
        cr.execute('DROP VIEW report_account_analytic_planning_stat_account')
    cr.execute('SELECT viewname FROM pg_views WHERE viewname = \'report_account_analytic_planning_stat\'')
    if cr.fetchall():
        cr.execute('DROP VIEW report_account_analytic_planning_stat')
    cr.execute('SELECT viewname FROM pg_views WHERE viewname = \'report_account_analytic_planning_stat_user\'')
    if cr.fetchall():
        cr.execute('DROP VIEW report_account_analytic_planning_stat_user')
    cr.execute('SELECT viewname FROM pg_views WHERE viewname = \'report_purchase_order_product\'')
    if cr.fetchall():
        cr.execute('DROP VIEW report_purchase_order_product')
    cr.execute('SELECT viewname FROM pg_views WHERE viewname = \'report_purchase_order_category\'')
    if cr.fetchall():
        cr.execute('DROP VIEW report_purchase_order_category')
    cr.execute('SELECT viewname FROM pg_views WHERE viewname = \'report_sale_order_product\'')
    if cr.fetchall():
        cr.execute('DROP VIEW report_sale_order_product')
    cr.execute('SELECT viewname FROM pg_views WHERE viewname = \'report_sale_order_category\'')
    if cr.fetchall():
        cr.execute('DROP VIEW report_sale_order_category')
    cr.execute('SELECT viewname FROM pg_views WHERE viewname = \'report_hr_timesheet_invoice_journal\'')
    if cr.fetchall():
        cr.execute('DROP VIEW report_hr_timesheet_invoice_journal')

    cr.execute('ALTER TABLE product_uom RENAME COLUMN factor to temp_column')
    cr.execute('ALTER TABLE product_uom ADD COLUMN factor NUMERIC(12,6)')
    cr.execute('UPDATE product_uom SET factor = temp_column')
    cr.execute('ALTER TABLE product_uom ALTER factor SET NOT NULL')
    cr.execute('ALTER TABLE product_uom DROP COLUMN temp_column')
cr.commit()


# ------------------------------------------------- #
# Drop name_uniq constraint on stock_production_lot #
# ------------------------------------------------- #

cr.execute('SELECT conname FROM pg_constraint where conname = \'stock_production_lot_name_uniq\'')
if cr.fetchall():
    cr.execute('ALTER TABLE stock_production_lot DROP CONSTRAINT stock_production_lot_name_uniq')
cr.commit()

# ------------------------------------ #
# Put country/state code in upper case #
# ------------------------------------ #

cr.execute('UPDATE res_country SET code = UPPER(code)')
cr.execute('UPDATE res_country_state SET code = UPPER(code)')
cr.commit()

# --------------------------------------------- #
# Add primary key on tables inherits ir_actions #
# --------------------------------------------- #

cr.execute('SELECT indexname FROm pg_indexes WHERE indexname = \'ir_act_report_xml_pkey\' and tablename = \'ir_act_report_xml\'')
if not cr.fetchall():
    cr.execute('ALTER TABLE ir_act_report_xml ADD PRIMARY KEY (id)')
cr.execute('SELECT indexname FROm pg_indexes WHERE indexname = \'ir_act_report_custom_pkey\' and tablename = \'ir_act_report_custom\'')
if not cr.fetchall():
    cr.execute('ALTER TABLE ir_act_report_custom ADD PRIMARY KEY (id)')
cr.execute('SELECT indexname FROm pg_indexes WHERE indexname = \'ir_act_group_pkey\' and tablename = \'ir_act_group\'')
if not cr.fetchall():
    cr.execute('ALTER TABLE ir_act_group ADD PRIMARY KEY (id)')
cr.execute('SELECT indexname FROm pg_indexes WHERE indexname = \'ir_act_execute_pkey\' and tablename = \'ir_act_execute\'')
if not cr.fetchall():
    cr.execute('ALTER TABLE ir_act_execute ADD PRIMARY KEY (id)')
cr.execute('SELECT indexname FROm pg_indexes WHERE indexname = \'ir_act_wizard_pkey\' and tablename = \'ir_act_wizard\'')
if not cr.fetchall():
    cr.execute('ALTER TABLE ir_act_wizard ADD PRIMARY KEY (id)')
cr.commit()

cr.close

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

