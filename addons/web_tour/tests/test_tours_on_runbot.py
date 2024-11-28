from odoo.tests import tagged, HttpCase
from odoo import tools
@tagged('post_install', '-at_install')
class TestOnboardingToursOnRunbot(HttpCase):

	@tools.mute_logger('odoo.http')
	def test_onboarding_tours_on_runbot(self):
		tours = self.env['web_tour.tour'].search([])	
		for tour in tours:
			self.start_tour(tour.url, tour.name, login='admin')
