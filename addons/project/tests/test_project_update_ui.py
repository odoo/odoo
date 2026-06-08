# -*- coding: utf-8 -*-

from odoo.tests import HttpCase, tagged

@tagged('post_install', '-at_install')
class TestProjectUpdateUi(HttpCase):

    def test_01_project_tour(self):
        # Enable milestones to avoid a different behavior when running the tour with or without demo data.
        # Indeed, when we check Milestones on the Settings tab of a newly created project,
        # we ensure milestones are globally enabled. If the feature was disabled, it causes a full page reload.
        # The tour step should then have a expectUnloadPage depending on whether milestones are already enabled.
        # As it is too complicated to determine this value from the tour itself, we avoid this page reload completely.
        self.env.ref('base.group_user').implied_ids |= self.env.ref('project.group_project_milestone')

        self.start_tour("/odoo", 'project_update_tour', login="admin")
        self.start_tour("/odoo", 'project_tour', login="admin")
