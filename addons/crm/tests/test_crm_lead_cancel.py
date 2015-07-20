# -*- coding: utf-8 -*-

from openerp.addons.crm.tests.test_crm_access_group_users import TestCrmAccessGroupUsers

class TestCrmLeadCancel(TestCrmAccessGroupUsers):

    def test_crm_lead_cancel(self):
        """ Tests for Crm Lead Cancel """
        CrmTeam = self.env['crm.team']
        crmlead = self.env.ref("crm.crm_case_1")

        # I set a new sale team (with Marketing at parent) giving access rights of salesman.
        team = CrmTeam.sudo(self.crm_res_users_salesmanager.id).create(
            dict(
                name="Phone Marketing",
                parent_id=self.env.ref("sales_team.crm_team_2").id,
            ))
        crmlead.sudo(self.crm_res_users_salesmanager.id).write(
            dict(
                team_id=team.id,
            ))

        # Salesman check unqualified lead .
        self.assertEqual(crmlead.stage_id.sequence, 1, 'Lead is in new stage')

        # Salesman escalate the lead to parent team.
        crmlead.case_escalate()

        # Salesman check the lead is correctly escalated to the parent team.
        self.assertEqual(crmlead.team_id.name, 'Marketing', 'Escalate lead to parent team')
