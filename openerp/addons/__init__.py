# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#    Copyright (C) 2010-2011 OpenERP s.a. (<http://openerp.com>).
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

""" Addons module.

This module serves to contain all OpenERP addons, across all configured addons
paths. For the code to manage those addons, see openerp.modules.

Addons are made available under `openerp.addons` after
openerp.tools.config.parse_config() is called (so that the addons paths are
known).

This module also conveniently reexports some symbols from openerp.modules.
Importing them from here is deprecated.

"""

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
