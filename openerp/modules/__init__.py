# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#    Copyright (C) 2010-2012 OpenERP s.a. (<http://openerp.com>).
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

""" Modules (also called addons) management.

"""

from . import db, graph, loading, migration, module, registry

from openerp.modules.loading import load_modules

from openerp.modules.module import get_modules, get_modules_with_version, \
    load_information_from_description_file, get_module_resource, get_module_path, \
    initialize_sys_path, load_openerp_module, init_module_models, adapt_version

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
