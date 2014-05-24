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
        crm_stage_stage = self.registry('crm.case.stage')
        crm_case_section = self.registry('crm.case.section')
        crm_lead = self.registry('crm.lead');
        crm_case_section_id = crm_case_section.create(cr, uid, {'name':'test_section'},context={})
        context = {'default_section_id': crm_case_section_id}
        
        ''' For create when default_section_id pass in context
                If same name is present than returns its id otherwise create new.
                 and link with given section.
        '''
        stage_type_id = crm_stage_stage.create(cr, uid, {'name':'First'}, {})
        self.assertEqual(stage_type_id, crm_stage_stage.create(cr, uid, {'name':'First'}, context=context))
        
        ''' For edit when default_section_id pass in context
                If same name is present than returns its id otherwise create new.
                and link with given section and remove old link with section and crm_lead.
        '''
        crm_case_section.write(cr, uid, [crm_case_section_id], {'stage_ids': [(4, stage_type_id),]}, context=context)
        lead_id = crm_lead.create(cr, uid, {'name':'Test1', 'stage_id': stage_type_id, 'section_id': crm_case_section_id})
        
        crm_stage_stage.write(cr, uid, [stage_type_id],{'name':'Second'}, context=context)

        stage_m2m_newlist = crm_case_section.browse(cr, uid, crm_case_section_id, context=context).stage_ids
        check_crm_lead_stage_id = crm_lead.browse(cr, uid, lead_id, context).stage_id.id
        crm_case_section_id_new = crm_stage_stage.search(cr, uid, [('name','=', 'Second')], context=context)
        
        self.assertIn(crm_case_section_id_new[0], [x.id for x in stage_m2m_newlist])
        self.assertEqual(check_crm_lead_stage_id, crm_case_section_id_new[0])

        ''' For unlink when default_section_id pass in context
                It will unlink relation, not delete.
        '''
        stage_m2m_oldlist = crm_case_section.browse(cr, uid, crm_case_section_id, context=context).stage_ids
        crm_stage_stage.unlink(cr, uid, crm_case_section_id_new, context=context)
        stage_m2m_newlist = crm_case_section.browse(cr, uid, crm_case_section_id, context=context).stage_ids
        
        self.assertEqual(len(stage_m2m_oldlist) -1, len(stage_m2m_newlist))
        
        unlink_id = crm_stage_stage.search(cr, uid, [('name','=', 'Second')], context=context)
        self.assertEqual(unlink_id, crm_case_section_id_new)