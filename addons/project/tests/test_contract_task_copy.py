# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (c) 2013-TODAY OpenERP S.A. <http://www.openerp.com>
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

from openerp.addons.project.tests.common import TestProject
from openerp.osv.orm import except_orm

class TestContractTaskCopy(TestProject):

    def test_contract_task_copy(self):
        """Testing Contract task copy"""
        cr, uid, = self.cr, self.uid,

        # Usefull models
        contract_obj = self.registry('account.analytic.account')
        project_obj = self.registry('project.project')
        task_obj = self.registry('project.task')

        # In order to test Contract project create new Contract Template.
        contract_template_id = contract_obj.create(cr, uid, {
            'name': 'Contract Template',
            'use_tasks': '1',
            'type': 'template'
            })

        # Create Task for project of this contract template.
        contract_template_set = contract_obj.browse(cr, uid, contract_template_id)
        task_id = task_obj.create(cr, uid, {
            'name': 'Project task',
            'project_id': contract_template_set.project_id.id
            })

        # Create contract based on this template.
        contract_id = contract_obj.create(cr, uid, {
            'name': 'Template of Contract',
            'template_id' : contract_template_id,
            'use_tasks': '1',
            })

        # Check that task for the contract project have been created same as the template.
        contract = contract_obj.browse(cr, uid, contract_id)
        self.assertTrue(len(contract.project_id.tasks) ==  1, "The no of task of contracts does not match.")
