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

def sugarcrm_fields_mapp(dict_sugar, openerp_dict):
    fields=[]
    data_lst = []
    for key,val in openerp_dict.items():
        if key not in fields and dict_sugar:
            fields.append(key)
            if isinstance(val, list) and val:
                data_lst.append(' '.join(map(lambda x : dict_sugar[x], val)))
            else:
                data_lst.append(dict_sugar.get(val,''))
    return fields,data_lst
