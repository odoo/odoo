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

import wizard
import pooler
from tools.translate import _
import datetime
from resource.faces import *
from new import classobj
import project_resource as proj

compute_form = """<?xml version="1.0" ?>
<form string="Compute Scheduling of Phases">

    <field name="project_id" colspan="4"/>

</form>"""

compute_fields = {
    'project_id': {'string':'Project', 'type':'many2one', 'relation': 'project.project'},

}

success_msg = """<?xml version="1.0" ?>
<form string="Compute Scheduling of Phases">
    <label string="Phase Scheduling completed successfully."/>
</form>"""

def phase_schedule(cr, uid, phase, start_date, calendar_id=False):
       pool = pooler.get_pool(cr.dbname)
       phase_pool = pool.get('project.phase')
       resource_pool = pool.get('resource.resource')
       uom_pool = pool.get('product.uom')
       wktime_cal = []
       resource_cal = False
       phase_resource = False
       if phase:
            resource_id = resource_pool.search(cr, uid, [('user_id','=',phase.responsible_id.id)])
            if resource_id:
                resource_obj = resource_pool.browse(cr, uid, resource_id)[0]
                leaves = proj.leaves_resource(cr, uid, calendar_id or False , resource_id, resource_obj.calendar_id.id)
                phase_resource = classobj(str(resource_obj.name), (Resource,), {'__doc__' : resource_obj.name, '__name__' : resource_obj.name, 'vacation' : tuple(leaves), 'efficiency' : resource_obj.time_efficiency})
            default_uom_id = uom_pool.search(cr, uid, [('name','=','Hour')])[0]
            avg_hours = uom_pool._compute_qty(cr, uid, phase.product_uom.id, phase.duration, default_uom_id)
            duration = str(avg_hours) + 'H'

            #    Creating a new project for each phase
            def Project():
                start = start_date
                minimum_time_unit = 1
                resource = phase_resource
                #    If project has working calendar else the default one would be considered
                if calendar_id:
                    working_days = proj.compute_working_calendar(cr, uid, calendar_id)
                    vacation = tuple(proj.leaves_resource(cr, uid, calendar_id))

                def phase():
                    effort = duration

            project = BalancedProject(Project)
            s_date = project.phase.start.to_datetime()
            e_date = project.phase.end.to_datetime()
            #    According to constraints on date start and date end on phase recalculation done
            if phase.constraint_date_start and str(s_date) < phase.constraint_date_start:
                start_date = datetime.datetime.strptime(phase.constraint_date_start, '%Y-%m-%d %H:%M:%S')
            else:
                start_date = s_date
            if phase.constraint_date_end and str(e_date) > phase.constraint_date_end:
                end_date= datetime.datetime.strptime(phase.constraint_date_end, '%Y-%m-%d %H:%M:%S')
                date_start = phase.constraint_date_end[:-3]
            else:
                end_date = e_date
                date_start = end_date

            #    Writing the dates back
            phase_pool.write(cr, uid, [phase.id], {'date_start' :start_date.strftime('%Y-%m-%d %H:%M:%S'), 'date_end' :end_date.strftime('%Y-%m-%d %H:%M:%S')}, context={'scheduler' :True})

            #    Recursive calling the next phases till all the phases are scheduled
            for phase in phase.next_phase_ids:
               if phase.state in ['draft','open','pending']:
                   phase_schedule(cr, uid, phase, date_start, phase.project_id.resource_calendar_id.id or False)
               else:
                   continue

#
class wizard_compute_phases(wizard.interface):

    def _compute_date(self, cr, uid, data, context):
        pool = pooler.get_pool(cr.dbname)
        project_pool = pool.get('project.project')
        phase_pool = pool.get('project.phase')

        # if project mentioned
        if data['form']['project_id']:
            project_id = project_pool.browse(cr, uid, data['form']['project_id'])
            phase_ids = phase_pool.search(cr, uid, [('project_id','=',project_id.id), ('state','in',['draft','open','pending']), ('previous_phase_ids','=',False)])

        # else all the draft,open,pending states phases taken
        else:
            phase_ids = phase_pool.search(cr, uid,[('state','in',['draft','open','pending']), ('previous_phase_ids','=',False)])

        phase_ids.sort()
        phase_objs = phase_pool.browse(cr, uid, phase_ids)
        for phase in phase_objs:
            start_date = phase.project_id.date_start
            if not phase.project_id.date_start:
                start_date = datetime.datetime.now().strftime("%Y-%m-%d")
            start_dt = datetime.datetime.strftime((datetime.datetime.strptime(start_date, "%Y-%m-%d")), "%Y-%m-%d %H:%M")
            calendar_id = phase.project_id.resource_calendar_id.id
            phase_schedule(cr, uid, phase, start_dt, calendar_id or False)
        return {}

    def phases_open_list(self, cr, uid, data, context):
        mod_obj = pooler.get_pool(cr.dbname).get('ir.model.data')
        act_obj = pooler.get_pool(cr.dbname).get('ir.actions.act_window')
        result = mod_obj._get_id(cr, uid, 'project_long_term', 'act_project_phase')
        id = mod_obj.read(cr, uid, [result], ['res_id'])[0]['res_id']
        result = act_obj.read(cr, uid, [id], context=context)[0]
        if data['form']['project_id']:
            result['domain'] = [('project_id', '=', data['form']['project_id'])]
        result['domain'] = [('state', 'not in', ['cancelled','done'])]
        return result

    states = {
        'init': {
            'actions': [],
            'result': {'type':'form', 'arch':compute_form, 'fields':compute_fields, 'state':[
                ('end', 'Cancel'),
                ('compute', 'Compute')

            ]},
        },
        'compute': {
            'actions': [_compute_date],
            'result': {'type': 'action', 'action':phases_open_list, 'state':'end'},
        },
    }

wizard_compute_phases('wizard.compute.phases')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
