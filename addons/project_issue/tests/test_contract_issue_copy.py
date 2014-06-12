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

from openerp.addons.mail.tests.common import TestMail
from openerp.tools import mute_logger


class TestIssue(TestMail):
    @mute_logger('openerp.addons.base.ir.ir_model', 'openerp.osv.orm')
    
    def setUp(self):
        super(TestIssue, self).setUp()
        
    def test_00_issue_process(self):
        """ Testing project issue from contract templates"""
        cr, uid = self.cr, self.uid   
             
        # Usefull models
        project_project = self.registry('project.project')
        project_issue = self.registry('project.issue')
        account_analytic_account = self.registry('account.analytic.account')
        
        # In order to test Contract project create a new Contract Template.
        template_id = account_analytic_account.create(cr, uid, {
            'name': 'Template Contract',
            'type': 'template',
            'use_issues': 1,
        })
        
        # I create Issue for project of this template.
        template_contract = account_analytic_account.browse(cr, uid, template_id)
        project_issue_id = project_issue.create(cr, uid, {
            'name': 'Test Issue',
            'project_id': template_contract.project_id.id
        })
        template_contract.refresh()
        
        self.assertTrue(len(template_contract.project_id.issue_ids) == 1, "project of the contract should have one issue")
        # I create a contract based on this template.
        contract_id = account_analytic_account.create(cr, uid, {
            'name': 'Contract Project',
            'use_issues': 1,
            'template_id': template_id,
        })

        # I check that issues for the contract project have been created same as the template.
        contract = account_analytic_account.browse(cr, uid, contract_id)
        self.assertTrue(len(contract.project_id.issue_ids) == 1, "The no of issue of contracts does not match with the no of issue of contract template.")
