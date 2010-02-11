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

from osv import fields, osv
import crm
from datetime import datetime, timedelta
from datetime import datetime, timedelta

class crm_opportunity(osv.osv):
    _name = 'crm.opportunity'
crm_opportunity()    
class crm_phonecall(osv.osv):
    _name = 'crm.phonecall'
crm_phonecall()    
class crm_meeting(osv.osv):
    _name = 'crm.meeting'
    _description = "Meeting Cases"
    _order = "id desc"
    _inherit = "crm.case"

    def _get_duration(self, cr, uid, ids, name, arg, context):
        res = {}
        for event in self.browse(cr, uid, ids, context=context):
            start = datetime.strptime(event.date, "%Y-%m-%d %H:%M:%S")
            res[event.id] = 0
            if event.date_deadline:
                end = datetime.strptime(event.date_deadline[:19], "%Y-%m-%d %H:%M:%S")
                diff = end - start
                duration =  float(diff.days)* 24 + (float(diff.seconds) / 3600)
                res[event.id] = round(duration, 2)
        return res

    def _set_duration(self, cr, uid, id, name, value, arg, context):
        event = self.browse(cr, uid, id, context=context)
        start = datetime.strptime(event.date, "%Y-%m-%d %H:%M:%S")
        end = start + timedelta(hours=value)
        cr.execute("UPDATE %s set date_deadline='%s' \
                        where id=%s"% (self._table, end.strftime("%Y-%m-%d %H:%M:%S"), id))
        return True

    _columns = {
        'priority': fields.selection(crm.AVAILABLE_PRIORITIES, 'Priority'), 
        'categ_id': fields.many2one('crm.case.categ', 'Category', \
                            domain="[('section_id','=',section_id),\
                            ('object_id.model', '=', 'crm.meeting')]", \
            help='Category related to the section.Subdivide the CRM cases \
independently or section-wise.'), 
        'duration': fields.function(_get_duration, method=True, \
                                    fnct_inv=_set_duration, string='Duration'),        
        'phonecall_id':fields.many2one ('crm.phonecall', 'Phonecall'),        
        'opportunity_id':fields.many2one ('crm.opportunity', 'Opportunity'),
    }

crm_meeting()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
