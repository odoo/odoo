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

import openerp

import interface
import print_xml
import print_fnc
import custom
import render
import int_to_text

import report_sxw

import printscreen

def render_report(cr, uid, ids, name, data, context=None):
    """
    Helper to call ``ir.actions.report.xml.render_report()``.
    """
    registry = openerp.modules.registry.RegistryManager.get(cr.dbname)
    return registry['ir.actions.report.xml'].render_report(cr, uid, ids, name, data, context)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

