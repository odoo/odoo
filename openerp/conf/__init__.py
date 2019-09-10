# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2011 OpenERP s.a. (<http://openerp.com>).
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

""" Library-wide configuration variables.

For now, configuration code is in openerp.tools.config. It is in mainly
unprocessed form, e.g. addons_path is a string with commas-separated
paths. The aim is to have code related to configuration (command line
parsing, configuration file loading and saving, ...) in this module
and provide real Python variables, e.g. addons_paths is really a list
of paths.

To initialize properly this module, openerp.tools.config.parse_config()
must be used.

"""

import deprecation

# Paths to search for OpenERP addons.
addons_paths = []

# List of server-wide modules to load. Those modules are supposed to provide
# features not necessarily tied to a particular database. This is in contrast
# to modules that are always bound to a specific database when they are
# installed (i.e. the majority of OpenERP addons). This is set with the --load
# command-line option.
server_wide_modules = []

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
