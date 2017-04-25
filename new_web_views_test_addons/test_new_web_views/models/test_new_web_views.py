from odoo import api, models, fields, _

class Test(models.Model):
	_name = "test_new_web_view.test_new_web_view"

	name = fields.Char()
	code = fields.Char()
	partner_id = fields.Many2one("res.partner", string="Partner")
	description = fields.Text()
	start_datetime = fields.Datetime(string="Start Datetime")
	test_lines = fields.One2many("test_new_web_view.lines", 'test_new_web_view_id', string="Test Lines")
	test_m2m = fields.Many2many("res.partner", string="Partners")


	@api.onchange('name')
	def onchange_name(self):
		self.code = self.name

class TestLines(models.Model):
	_name = 'test_new_web_view.lines'

	name = fields.Char(required=True)
	code = fields.Char()
	test_new_web_view_id = fields.Many2one("test_new_web_view.test_new_web_view", string="Test View")
