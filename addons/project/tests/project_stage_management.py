# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (c) 2012-TODAY OpenERP S.A. <http://openerp.com>
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
from openerp.osv.orm import except_orm
from openerp.tests import common


class TestCrmStagesCase(common.TransactionCase):
    def setUp(self):
        super(TestCrmStagesCase, self).setUp()
        
    def test_00_stage_management(self):
        
        cr, uid = self.cr, self.uid
        project_project = self.registry('project.project')
        project_task_type= self.registry('project.task.type')
        project_task = self.registry('project.task');
        project_project_id = project_project.create(cr, uid, {'name':'Project1'},context={})
        context = {'default_project_id': project_project_id}
        
        ''' For create when default_project_id pass in context
                If same name is present than returns its id otherwise create new.
                and link with given project
        '''
        
        task_type_id = project_task_type.create(cr, uid, {'name':'First'}, {})
        self.assertEqual(task_type_id, project_task_type.create(cr, uid, {'name':'First'}, context=context))
        
        ''' For edit when default_project_id pass in context
                If same name is present than returns its id otherwise create new.
                 and link with given project and remove old link with project and project_task.
        '''
        project_project.write(cr, uid, [project_project_id], {'type_ids': [(4, task_type_id),]}, context=context)
        task_id = project_task.create(cr, uid, {'name':'Test1', 'stage_id': task_type_id, 'project_id':project_project_id})
        context.update({'stage_model':'project.task'})
        
        project_task_type.write(cr, uid, [task_type_id],{'name':'Second'}, context=context)
        
        stage_m2m_newlist = project_project.browse(cr, uid, project_project_id, context=context).type_ids
        check_project_task_stage_id = project_task.browse(cr, uid, task_id, context).stage_id.id
        task_type_id_new = project_task_type.search(cr, uid, [('name','=', 'Second')], context=context)
        
        self.assertIn(task_type_id_new[0], [x.id for x in stage_m2m_newlist])
        self.assertEqual(check_project_task_stage_id, task_type_id_new[0])
        
        ''' For unlink when default_project_id pass in context
                It will unlink relation, not delete.
        '''
        stage_m2m_oldlist = project_project.browse(cr, uid, project_project_id, context=context).type_ids
        project_task_type.unlink(cr, uid, task_type_id_new, context=context)
        stage_m2m_newlist = project_project.browse(cr, uid, project_project_id, context=context).type_ids
        
        self.assertEqual(len(stage_m2m_oldlist) -1, len(stage_m2m_newlist))
        
        unlink_id = project_task_type.search(cr, uid, [('name','=', 'Second')], context=context)
        self.assertEqual(unlink_id, task_type_id_new)
        