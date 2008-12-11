# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution    
#    Copyright (C) 2004-2008 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from osv import fields, osv
from locale import localeconv

class lang(osv.osv):
    _name = "res.lang"
    _description = "Languages"
     
    def _get_default_date_format(self,cursor,user,context={}):
        return '%Y-%m-%d'
    
    def _get_default_time_format(self,cursor,user,context={}):
        return '%H:%M:%S'
    
    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'code': fields.char('Code', size=5, required=True),
        'translatable': fields.boolean('Translatable'),
        'active': fields.boolean('Active'),
        'direction': fields.selection([('ltr', 'Left-to-Right'), ('rtl', 'Right-to-Left')], 'Direction',required=True),
        'date_format':fields.char('Date Format',size=64,required=True),
        'time_format':fields.char('Time Format',size=64,required=True),
        'grouping':fields.char('Separator Format',size=64,required=True,help="The Separator Format should be like [,n] where 0 < n :starting from Unit digit.-1 will end the separation. e.g. [3,2,-1] will represent 106500 to be 1,06,500;[1,2,-1] will represent it to be 106,50,0;[3] will represent it as 106,500. Provided ',' as the thousand separator in each case."),        
        'decimal_point':fields.char('Decimal Separator', size=64,required=True),
        'thousands_sep':fields.char('Thousands Separator',size=64),
        'legend':fields.text('Legends for Date and Time Formats',readonly=True),
    }
    _defaults = {
        'active': lambda *a: 1,
        'translatable': lambda *a: 0,
        'direction': lambda *a: 'ltr',
        'date_format':_get_default_date_format,
        'time_format':_get_default_time_format,
        'grouping':lambda *a: '[]',
        'decimal_point':lambda *a: '.',
        'thousands_sep':lambda *a: ',',
        'legend': lambda *a: '%a  - Abbreviated weekday name.\
\n%A  - Full weekday name.\
\n%b  - Abbreviated month name.\
\n%B  - Full month name.     \
\n%c  - Appropriate date and time representation.\
\n%d  - Day of the month as a decimal number [01,31].\
\n%H  - Hour (24-hour clock) as a decimal number [00,23].\
\n%I  - Hour (12-hour clock) as a decimal number [01,12].\
\n%j  - Day of the year as a decimal number [001,366].\
\n%m  - Month as a decimal number [01,12].\
\n%M  - Minute as a decimal number [00,59].\
\n%p  - Equivalent of either AM or PM.\
\n%S  - Second as a decimal number [00,61].\
\n%U  - Week number of the year (Sunday as the first day of the week) as a decimal number [00,53]. All days in a new year preceding the first Sunday are considered to be in week 0.\
\n%w  - Weekday as a decimal number [0(Sunday),6].\
\n%W  - Week number of the year (Monday as the first day of the week) as a decimal number [00,53]. All days in a new year preceding the first Monday are considered to be in week 0.\
\n%x  - Appropriate date representation.\
\n%X  - Appropriate time representation.\
\n%y  - Year without century as a decimal number [00,99].\
\n%Y  - Year with century as a decimal number.\
\n ==========================================\
\n\nExamples:\
\n1.  %c ==> Fri Dec  5 18:25:20 2008\
\n2.  %a ,%A ==> Fri, Friday\
\n3.  %x ,%X ==> 12/05/08, 18:25:20\
\n4.  %b, %B ==> Dec, December\
\n5.  %y, %Y ==> 08, 2008\
\n6.  %d, %m ==> 05, 12\
\n7.  %H:%M:%S ==> 18:25:20\
\n8.  %I:%M:%S %p ==> 06:25:20 PM\
\n9.  %j ==> 340\
\n10. %S ==> 20\
\n11. %U or %W ==> 48 (49th week)\
\n12. %w ==> 5 ( Friday is the 6th day)',
    }
    
    def _group(self,cr,uid,ids,s, monetary=False):
        conv = localeconv()

        lang_obj=self.browse(cr,uid,ids[0])
        thousands_sep = lang_obj.thousands_sep or conv[monetary and 'mon_thousands_sep' or 'thousands_sep']

        grouping = eval(lang_obj.grouping)
        
        if not grouping:
            return (s, 0)
        result = ""
        seps = 0
        spaces = ""
        if s[-1] == ' ':
            sp = s.find(' ')
            spaces = s[sp:]
            s = s[:sp]
        while s and grouping:
            # if grouping is -1, we are done
            if grouping[0] == -1:
                break
            # 0: re-use last group ad infinitum
            elif grouping[0] != 0:
                #process last group
                group = grouping[0]
                grouping = grouping[1:]
            if result:
                result = s[-group:] + thousands_sep + result
                seps += 1
            else:
                result = s[-group:]
            s = s[:-group]
            if s and s[-1] not in "0123456789":
                # the leading string is only spaces and signs
                return s + result + spaces, seps
        if not result:
            return s + spaces, seps
        if s:
            result = s + thousands_sep + result
            seps += 1
        return result + spaces, seps

    def format(self,cr,uid,ids,percent, value, grouping=False, monetary=False):
        """ Format() will return the language-specific output for float values"""

        if percent[0] != '%':
            raise ValueError("format() must be given exactly one %char format specifier")

        lang_obj=self.browse(cr,uid,ids[0])
        
        formatted = percent % value
        # floats and decimal ints need special action!
        if percent[-1] in 'eEfFgG':
            seps = 0
            parts = formatted.split('.')
            
            if grouping:
                parts[0], seps = self._group(cr,uid,ids,parts[0], monetary=monetary)

            decimal_point=lang_obj.decimal_point
            formatted = decimal_point.join(parts)
            while seps:
                sp = formatted.find(' ')
                if sp == -1: break
                formatted = formatted[:sp] + formatted[sp+1:]
                seps -= 1
        elif percent[-1] in 'diu':
            if grouping:
                formatted = self._group(cr,uid,ids,formatted, monetary=monetary)[0]

        return formatted

#    import re, operator
#    _percent_re = re.compile(r'%(?:\((?P<key>.*?)\))?'
#                             r'(?P<modifiers>[-#0-9 +*.hlL]*?)[eEfFgGdiouxXcrs%]')

lang()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
