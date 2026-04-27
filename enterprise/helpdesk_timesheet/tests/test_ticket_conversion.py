# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import Form

from odoo.addons.helpdesk.tests.common import HelpdeskCommon
from odoo.addons.project.tests.test_project_base import TestProjectCommon

class TestTicketConversion(TestProjectCommon, HelpdeskCommon):

    @classmethod
    def setUpClass(cls):
        super(TestTicketConversion, cls).setUpClass()

        cls.ticket_1 = cls.env['helpdesk.ticket'].with_user(cls.helpdesk_user).create({
            'name': 'test ticket 1',
            'team_id': cls.test_team.id,
        })

        cls.project_helpdesk = cls.env['project.project'].with_context({'mail_create_nolog': True}).create({
            'name': 'Helpdesk',
        })

        cls.test_team.write({
            'project_id': cls.project_helpdesk.id,
        })

    def test_wizard_default_project(self):
        form = Form(self.env['helpdesk.ticket.convert.wizard'].with_context({'to_convert': [self.ticket_1.id]}))

        self.assertEqual(form.project_id, self.project_helpdesk, "The helpdesk team project should be selected by default")
