# -*- encoding: utf-8 -*-
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
import addons
import tools
import pytz
import time
from osv import osv, fields
from datetime import datetime, timedelta

class lunch_alert(osv.Model):
    """ lunch alert """
    _name = 'lunch.alert'
    _description = 'lunch alert'
    _columns = {
        'message' : fields.text('Message',size=256, required=True),
        'active' : fields.boolean('Active'),
        'day' : fields.selection([('specific','Specific day'), ('week','Every Week'), ('days','Every Day')], 'Recurrency'),
        'specific' : fields.date('Day'),
        'monday' : fields.boolean('Monday'),
        'tuesday' : fields.boolean('Tuesday'),
        'wednesday' : fields.boolean('Wednesday'),
        'thursday' : fields.boolean('Thursday'),
        'friday' : fields.boolean('Friday'),
        'saturday' : fields.boolean('Saturday'),
        'sunday' :  fields.boolean('Sunday'),
        'active_from': fields.float('Between',required=True),
        'active_to': fields.float('And',required=True),
    }