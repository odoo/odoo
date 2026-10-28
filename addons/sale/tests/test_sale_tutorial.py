from odoo.tests import tagged

from odoo.addons.web_tutorial.tests.common import TutorialTourCase


@tagged('post_install', '-at_install')
class TestSaleTutorial(TutorialTourCase):

    def test_sale_tutorial(self):
        self.start_tutorial_tour('sale_tutorial')
