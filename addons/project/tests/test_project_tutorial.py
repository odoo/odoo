from odoo.tests import tagged

from odoo.addons.web_tutorial.tests.common import TutorialTourCase


@tagged('post_install', '-at_install')
class TestProjectTutorial(TutorialTourCase):

    def test_project_tutorial(self):
        self.start_tutorial_tour('project_tutorial')
