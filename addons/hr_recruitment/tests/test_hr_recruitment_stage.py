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


class TestHrRecruitmentStage(common.TransactionCase):
    def setUp(self):
        super(TestHrRecruitmentStage, self).setUp()
        
    def test_00_stage_management(self):
        cr, uid = self.cr, self.uid
        hr_job = self.registry('hr.job')
        hr_recruitment_stage= self.registry('hr.recruitment.stage')
        hr_applicant = self.registry('hr.applicant');
        hr_job_id = hr_job.create(cr, uid, {'name':'test_section'},context={})
        context = {'default_job_id': hr_job_id}
        
        ''' For create when default_job_id pass in context
                If same name is present than returns its id otherwise create new.
                 and link with given job.
        '''
        
        check_len_id = hr_recruitment_stage.create(cr, uid, {'name':'First'},{})
        self.assertEqual(check_len_id, hr_recruitment_stage.create(cr, uid, {'name':'First'}, context=context))
        
        ''' For edit when default_job_id pass in context
                If same name is present than returns its id otherwise create new.
                and link with given job and remove old link with job and project_task.        
         '''
        hr_job.write(cr, uid, [hr_job_id],  {'stage_ids': [(4, check_len_id),]}, context=context)
        hr_recruitment_id = hr_applicant.create(cr, uid, {'name':'Test1', 'stage_id': check_len_id, 'job_id':hr_job_id})
        
        hr_recruitment_stage.write(cr, uid, [check_len_id],{'name':'Second'}, context=context)
        
        stage_m2m_newlist = hr_job.browse(cr, uid, hr_job_id, context=context).stage_ids
        check_hr_recruitment_stage_id = hr_applicant.browse(cr, uid, hr_recruitment_id, context).stage_id.id
        hr_recruitment_stage_id_new = hr_recruitment_stage.search(cr, uid, [('name','=', 'Second')], context=context)
        
        self.assertIn(hr_recruitment_stage_id_new[0],  [x.id for x in stage_m2m_newlist])
        self.assertEqual(check_hr_recruitment_stage_id, hr_recruitment_stage_id_new[0])
        
        ''' For unlink when default_job_id pass in context
                It will unlink relation, not delete.
        '''
        stage_m2m_oldlist = hr_job.browse(cr, uid, hr_job_id, context=context).stage_ids
        hr_recruitment_stage.unlink(cr, uid, hr_recruitment_stage_id_new, context=context)
        stage_m2m_newlist = hr_job.browse(cr, uid, hr_job_id, context=context).stage_ids
        
        self.assertEqual(len(stage_m2m_oldlist) -1, len(stage_m2m_newlist))
        unlink_id = hr_recruitment_stage.search(cr, uid, [('name','=', 'Second')], context=context)
        self.assertEqual(unlink_id, hr_recruitment_stage_id_new)
 
