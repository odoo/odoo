from odoo.tests import tagged

from odoo.addons.web_tutorial.tests.common import TutorialTourCase


@tagged('post_install', '-at_install')
class TestCrmTutorial(TutorialTourCase):

    def test_crm_tutorial(self):
        self.start_tutorial_tour('crm_tutorial')
