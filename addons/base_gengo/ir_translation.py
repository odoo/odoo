# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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

from osv import fields,osv,orm
import os
import openerp 
import tools

class ir_translation(osv.osv):
    _name = "ir.translation"
    _description="Translation"
    _inherit="ir.translation"
    _columns = {
        'gengo_comment':fields.text("comments", help="Comment for translators"),
        'gengo_translation':fields.boolean("Translation", help='This term has to be translated by Gengo automatically'),
        'gengo_control':fields.boolean('Active'),
    
    }
    
    _defaults = {
        'gengo_control':False,
    }

