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
import datetime
from resource.faces import *
from new import classobj

import wizard
import pooler
from tools.translate import _

import working_calendar as wkcal

compute_form = """<?xml version="1.0" ?>
<form string="Compute Scheduling of Phases">

    <field name="project_id" colspan="4"/>

</form>"""

compute_fields = {
    'project_id': {'string':'Project', 'type':'many2one', 'relation':'project.project', 'help': 'If you do not specify project then it will take All projects with state=draft, open, pending'},

}

class wizard_compute_phases(wizard.interface):
    def _phase_schedule(self, cr, uid, phase, start_date, calendar_id=False, context={}):

       """Schedule phase with the start date till all the next phases are completed.

       Arguements: start_dsate -- start date for the phase
                   calendar_id -- working calendar of the project

       """
       pool = pooler.get_pool(cr.dbname)
       phase_obj = pool.get('project.phase')
       resource_obj = pool.get('resource.resource')
       uom_obj = pool.get('product.uom')
       phase_resource_obj = False
       if phase:
            leaves = []
            time_efficiency = 1.0
            resource_id = resource_obj.search(cr, uid, [('user_id', '=', phase.responsible_id.id)])

            if resource_id:
                # Create a new resource object with
                # all the attributes of the Resource Class
                resource = resource_obj.browse(cr, uid, resource_id, context=context)[0]
                time_efficiency = resource.time_efficiency
                leaves = wkcal.compute_leaves(cr, uid, calendar_id , resource.id, resource.calendar_id.id)
            phase_resource_obj = classobj((phase.responsible_id.name.encode('utf8')), (Resource,),
                                               {'__doc__': phase.responsible_id.name,
                                                '__name__': phase.responsible_id.name,
                                                'vacation': tuple(leaves),
                                                'efficiency': time_efficiency
                                                })
            default_uom_id = uom_obj.search(cr, uid, [('name','=','Hour')])[0]
            avg_hours = uom_obj._compute_qty(cr, uid, phase.product_uom.id, phase.duration, default_uom_id)
            duration = str(avg_hours) + 'H'
            # Create a new project for each phase
            def Project():
                start = start_date
                minimum_time_unit = 1
                resource = phase_resource_obj
                # If project has working calendar then that
                # else the default one would be considered
                if calendar_id:
                    working_days = wkcal.compute_working_calendar(cr, uid, calendar_id, context=context)
                    vacation = tuple(wkcal.compute_leaves(cr, uid, calendar_id))

                def phase():
                    effort = duration

            project = BalancedProject(Project)
            s_date = project.phase.start.to_datetime()
            e_date = project.phase.end.to_datetime()
            # Recalculate date_start and date_end
            # according to constraints on date start and date end on phase
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
            # Write the calculated dates back
            ctx = context.copy()
            ctx.update({'scheduler': True})
            phase_obj.write(cr, uid, [phase.id], {'date_start': start_date.strftime('%Y-%m-%d %H:%M:%S'),
                                                  'date_end': end_date.strftime('%Y-%m-%d %H:%M:%S')},
                                                   context=ctx)
            # Recursive call till all the next phases scheduled
            for phase in phase.next_phase_ids:
               if phase.state in ['draft','open','pending']:
                   id_cal = phase.project_id.resource_calendar_id and phase.project_id.resource_calendar_id.id or False
                   self._phase_schedule(cr, uid, phase, date_start, id_cal, context=context)
               else:
                   continue

    def _compute_date(self, cr, uid, data, context={}):
        """
        Compute the phases for scheduling.
        """
        pool = pooler.get_pool(cr.dbname)
        project_obj = pool.get('project.project')
        phase_obj = pool.get('project.phase')
        if data['form']['project_id']:        # If project mentioned find its phases
            project_id = project_obj.browse(cr, uid, data['form']['project_id'], context=context)
            phase_ids = phase_obj.search(cr, uid, [('project_id', '=', project_id.id),
                                                  ('state', 'in', ['draft', 'open', 'pending']),
                                                  ('previous_phase_ids', '=', False)
                                                  ])
        else:                        # Else take all the draft,open,pending states phases
            phase_ids = phase_obj.search(cr, uid,[('state', 'in', ['draft', 'open', 'pending']),
                                                  ('previous_phase_ids', '=', False)
                                                  ], context=context)
        phase_ids.sort()
        phases = phase_obj.browse(cr, uid, phase_ids, context=context)
        for phase in phases:
            start_date = phase.project_id.date_start
            if not phase.project_id.date_start:
                start_date = datetime.datetime.now().strftime("%Y-%m-%d")
            start_dt = datetime.datetime.strftime((datetime.datetime.strptime(start_date, "%Y-%m-%d")), "%Y-%m-%d %H:%M")
            calendar_id = phase.project_id.resource_calendar_id and phase.project_id.resource_calendar_id.id or False
            self._phase_schedule(cr, uid, phase, start_dt, calendar_id, context=context)
        return {}

    def _open_phases_list(self, cr, uid, data, context):
        """
        Return the scheduled phases list.
        """
        pool = pooler.get_pool(cr.dbname)
        mod_obj = pool.get('ir.model.data')
        act_obj = pool.get('ir.actions.act_window')
        result = mod_obj._get_id(cr, uid, 'project_long_term', 'act_project_phase')
        id = mod_obj.read(cr, uid, [result], ['res_id'])[0]['res_id']
        result = act_obj.read(cr, uid, [id], context=context)[0]
        result['domain'] = [('state', 'not in', ['cancelled','done'])]
        if data['form']['project_id']:
            result['domain'] = [('project_id', '=', data['form']['project_id']),
                                ('state', 'not in', ['cancelled','done'])]
        return result

    states = {
        'init': {
            'actions': [],
            'result': {'type': 'form', 'arch': compute_form, 'fields': compute_fields, 'state':[
                ('end', 'Cancel'),
                ('compute', 'Compute')

            ]},
        },
        'compute': {
            'actions': [_compute_date],
            'result': {'type': 'action', 'action': _open_phases_list, 'state': 'end'},
        },
    }
wizard_compute_phases('wizard.compute.phases')
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
