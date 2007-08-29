# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
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

# ------------------------------ #
# drop not null on ir_attachment #
# ------------------------------ #

cr.execute('ALTER TABLE ir_attachment \
		ALTER COLUMN res_model DROP NOT NULL, \
		ALTER COLUMN res_id DROP NOT NULL')
cr.commit()

cr.close
