# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.addons.sale_timesheet.tests.common import TestCommonSaleTimesheet


@tagged("-at_install", "post_install", "helpdesk_sale_timesheet")
class TestSaleTimesheetInTicket(TestCommonSaleTimesheet):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.helpdesk_team = cls.env['helpdesk.team'].create({
            'name': 'Test Team',
            'use_helpdesk_timesheet': True,
            'use_helpdesk_sale_timesheet': True,
            'project_id': cls.project_task_rate.id,
            'use_sla': True,
        })

    def test_sla_customer_restriction(self):
        """
        Creating an SLA Policy with a restricted customer
        shouldn't apply to tickets with another customer
        """
        # create 2 distinct customers/partners
        partner_in_sla = self.env['res.partner'].create({
            "name": "Partner in SLA",
        })
        partner_not_in_sla = self.env['res.partner'].create({
            "name": "Partner in not in SLA",
        })
        helpdesk_stage = self.env["helpdesk.stage"].create({
            "name": "New",
            "sequence": 0,
        })
        # create an SLA policy that applies to only 1 of those customer
        sla_policy = self.env['helpdesk.sla'].create({
            "name": "SLA Policy",
            "partner_ids": [partner_in_sla.id],
            "team_id": self.helpdesk_team.id,
            "priority": "0",
            "stage_id": helpdesk_stage.id,
        })
        # create a ticket that has the customer with the SLA policy
        ticket_sla_present = self.env["helpdesk.ticket"].create({
            "name": "Ticket SLA Present",
            "partner_id": partner_in_sla.id,
            "team_id": self.helpdesk_team.id,
            "priority": "0",
            "stage_id": helpdesk_stage.id,
        })
        # check for the presence of the policy on the ticket
        self.assertTrue(sla_policy in ticket_sla_present.sla_status_ids.sla_id,
                        "SLA Policy should be present on the ticket")
        # create a ticket that has the other customer not in the SLA policy
        ticket_sla_not_present = self.env["helpdesk.ticket"].create({
            "name": "Ticket without SLA",
            "partner_id": partner_not_in_sla.id,
            "team_id": self.helpdesk_team.id,
            "priority": "0",
            "stage_id": helpdesk_stage.id,
        })
        # check for the lack of presence of the policy on the ticket
        self.assertFalse(sla_policy in ticket_sla_not_present.sla_status_ids.sla_id,
                         "SLA Policy shouldn't be present on the ticket")
