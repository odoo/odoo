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

from datetime import date, timedelta, datetime
import time

from osv import fields, osv

class project_project(osv.osv):
    _inherit = 'project.project'

    def write(self, cr, uid, ids, vals, *args, **kwargs):
        if isinstance(ids, (int, long)):
            ids = [ids]
        if vals.get('date', False):
            data_project = self.browse(cr, uid, ids)
            for prj in data_project:
                if isinstance(vals['date'], datetime):
                    new_end_date = vals['date'].date()
                elif isinstance(vals['date'], date):
                    new_end_date = vals['date']
                else:
                    new_end_date = date(*time.strptime(vals['date'],'%Y-%m-%d')[:3])
                if prj.date:
                    old_end_date = date(*time.strptime(prj.date,'%Y-%m-%d')[:3])
                    for task in prj.tasks:
                        if task.date_start:
                            start_dt = (date(*time.strptime(str(task.date_start),'%Y-%m-%d  %H:%M:%S')[:3])+(new_end_date-old_end_date)).strftime('%Y-%m-%d %H:%M:%S')
                            if task.date_deadline:
                                deadline_dt = (datetime(*time.strptime(str(task.date_deadline),'%Y-%m-%d')[:3])+(new_end_date-old_end_date)).strftime('%Y-%m-%d')
                                self.pool.get('project.task').write(cr, uid, [task.id], {'date_start':start_dt, 'date_deadline':deadline_dt})
                            else:
                                self.pool.get('project.task').write(cr, uid, [task.id], {'date_start':start_dt})
        return super(project_project,self).write(cr, uid, ids, vals, *args, **kwargs)

project_project()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
