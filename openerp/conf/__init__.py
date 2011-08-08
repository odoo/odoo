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

"""

import deprecation

# Maximum number of threads processing concurrently cron jobs.
# Access to this variable must be thread-safe; they have to be done
# through the functions in openerp.cron.
max_cron_threads = 4 # Actually the default value here is meaningless,
                     # look at tools.config for the default value.

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
