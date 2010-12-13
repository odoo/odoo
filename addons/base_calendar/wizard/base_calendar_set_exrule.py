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

from base_calendar import base_calendar
from osv import fields, osv
from tools.translate import _
import tools
import re


months = {
    1: "January", 2: "February", 3: "March", 4: "April", \
    5: "May", 6: "June", 7: "July", 8: "August", 9: "September", \
    10: "October", 11: "November", 12: "December"
}

class base_calendar_set_exrule(osv.osv_memory):
    """
    Set Exrule.
    """

    _name = "base.calendar.set.exrule"
    _description = "Set Exrule"

    _columns = {
      'freq': fields.selection([('None', 'No Repeat'), \
                                ('secondly', 'Secondly'), \
                                ('minutely', 'Minutely'), \
                                ('hourly', 'Hourly'), \
                                ('daily', 'Daily'), \
                                ('weekly', 'Weekly'), \
                                ('monthly', 'Monthly'), \
                                ('yearly', 'Yearly')], 'Frequency',required=True),
        'interval': fields.integer('Interval'),
        'count': fields.integer('Count'),
        'mo': fields.boolean('Mon'),
        'tu': fields.boolean('Tue'),
        'we': fields.boolean('Wed'),
        'th': fields.boolean('Thu'),
        'fr': fields.boolean('Fri'),
        'sa': fields.boolean('Sat'),
        'su': fields.boolean('Sun'),
        'select1': fields.selection([('date', 'Date of month'), \
                                    ('day', 'Day of month')], 'Option'),
        'day': fields.integer('Date of month'),
        'week_list': fields.selection([('MO', 'Monday'), ('TU', 'Tuesday'), \
                                   ('WE', 'Wednesday'), ('TH', 'Thursday'), \
                                   ('FR', 'Friday'), ('SA', 'Saturday'), \
                                   ('SU', 'Sunday')], 'Weekday'),
        'byday': fields.selection([('1', 'First'), ('2', 'Second'), \
                                   ('3', 'Third'), ('4', 'Fourth'), \
                                   ('5', 'Fifth'), ('-1', 'Last')], 'By day'),
        'month_list': fields.selection(months.items(),'Month'),
        'end_date': fields.date('Repeat Until'),

    }

    def view_init(self, cr, uid, fields, context=None):
        """
        This function checks for precondition before wizard executes
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param fields: List of fields for default value
        @param context: A standard dictionary for contextual values
        """
        if context is None: 
            context = {}
        event_obj = self.pool.get(context.get('active_model'))
        for event in event_obj.browse(cr, uid, context.get('active_ids', []), context=context):
            if not event.rrule:
                raise osv.except_osv(_("Warning !"), _("Please Apply Recurrency before applying Exception Rule."))
        return False

    def compute_exrule_string(self, cr, uid, ids, context=None):
        """
        Compute rule string.
        @param self: the object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param datas: dictionary of freq and interval value.
        @return: string value which compute FREQILY;INTERVAL
        """

        weekdays = ['mo', 'tu', 'we', 'th', 'fr', 'sa', 'su']
        weekstring = ''
        monthstring = ''
        yearstring = ''
        if context is None: 
            context = {}
        ex_id = base_calendar.base_calendar_id2real_id(context.get('active_id', False))
        model = context.get('model', False)
        model_obj = self.pool.get(model)
        for datas in self.read(cr, uid, ids, context=context):
            freq = datas.get('freq')
            if freq == 'None':
                model_obj.write(cr, uid, ex_id,{'exrule': ''})
                return{}

            interval_srting = datas.get('interval') and (';INTERVAL=' + str(datas.get('interval'))) or ''

            if freq == 'weekly':

                byday = map(lambda x: x.upper(), filter(lambda x: datas.get(x) and x in weekdays, datas))
                if byday:
                    weekstring = ';BYDAY=' + ','.join(byday)

            elif freq == 'monthly':
                if datas.get('select1')=='date' and (datas.get('day') < 1 or datas.get('day') > 31):
                    raise osv.except_osv(_('Error!'), ("Please select proper Day of month"))
                if datas.get('select1')=='day':
                    monthstring = ';BYDAY=' + datas.get('byday') + datas.get('week_list')
                elif datas.get('select1')=='date':
                    monthstring = ';BYMONTHDAY=' + str(datas.get('day'))

            elif freq == 'yearly':
                if datas.get('select1')=='date' and (datas.get('day') < 1 or datas.get('day') > 31):
                    raise osv.except_osv(_('Error!'), ("Please select proper Day of month"))
                bymonth = ';BYMONTH=' + str(datas.get('month_list'))
                if datas.get('select1')=='day':
                    bystring = ';BYDAY=' + datas.get('byday') + datas.get('week_list')
                elif datas.get('select1')=='date':
                    bystring = ';BYMONTHDAY=' + str(datas.get('day'))
                yearstring = bymonth + bystring

            if datas.get('end_date'):
                datas['end_date'] = ''.join((re.compile('\d')).findall(datas.get('end_date'))) + '235959Z'
            enddate = (datas.get('count') and (';COUNT=' + str(datas.get('count'))) or '') +\
                                 ((datas.get('end_date') and (';UNTIL=' + datas.get('end_date'))) or '')

            exrule_string = 'FREQ=' + freq.upper() + weekstring + interval_srting \
                                + enddate + monthstring + yearstring

            model_obj.write(cr, uid, ex_id,{'exrule': exrule_string})
            return {}

        _defaults = {
         'freq': lambda *x: 'None',
         'select1': lambda *x: 'date',
         'interval': lambda *x: 1,
    }

base_calendar_set_exrule()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: