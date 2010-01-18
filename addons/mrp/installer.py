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
from osv import fields, osv

class mrp_installer(osv.osv_memory):
    _name = 'mrp.installer'
    _inherit = 'res.config.installer'

    _columns = {
        # Manufacturing Resource Planning
        'stock_location':fields.boolean('Advanced Routes'),
        'mrp_jit':fields.boolean('Just In Time Scheduling'),
        'mrp_operations':fields.boolean('Manufacturing Operations'),
        'mrp_subproduct':fields.boolean('MRP Subproducts'),
        'mrp_repair':fields.boolean('Repairs'),
        }
mrp_installer()
