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
import tools
import pytz
import time
from datetime import datetime, timedelta, date
from dateutil import parser
import dateutil

def sugarcrm_fields_mapp(dict_sugar, openerp_dict, context=None):
    if not context:
        context = {}
    if 'tz' in context and context['tz']:
          time_zone = context['tz']
    else:
          time_zone = tools.get_server_timezone()
    au_tz = pytz.timezone(time_zone)
    fields=[]
    data_lst = []
    for key,val in openerp_dict.items():
        if key not in fields and dict_sugar:
            fields.append(key)
            if isinstance(val, list) and val:
                #Allow to print a bit more pretty way long list of data in the same field
                if len(val) >= 1 and val[0] == "__prettyprint__":
                    val = val[1:]
                    data_lst.append('\n\n'.join(map(lambda x : x + ": " + dict_sugar.get(x,''), val)))
                elif val[0] == '__datetime__':
                    val = val[1]
                    if dict_sugar.get(val) and len(dict_sugar.get(val))<=10:
                        updated_dt = date.fromtimestamp(time.mktime(time.strptime(dict_sugar.get(val), '%Y-%m-%d'))) or False
                    elif  dict_sugar.get(val):
                        convert_date = datetime.strptime(dict_sugar.get(val), '%Y-%m-%d %H:%M:%S')
                        edate = convert_date.replace(tzinfo=au_tz)
                        au_dt = au_tz.normalize(edate.astimezone(au_tz))
                        updated_dt = datetime(*au_dt.timetuple()[:6]).strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        updated_dt = False    
                    data_lst.append(updated_dt)
                else:
                    if key == 'duration':
                        data_lst.append('.'.join(map(lambda x : dict_sugar.get(x,''), val)))
                    else:
                        data_lst.append(' '.join(map(lambda x : dict_sugar.get(x,''), val)))
            else:
                data_lst.append(dict_sugar.get(val,''))
    return fields,data_lst
