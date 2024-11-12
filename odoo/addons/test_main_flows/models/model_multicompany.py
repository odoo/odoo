from odoo import models, fields


class TestModel_Multicompany(models.Model):
    _name = 'test.model_multicompany'
    _description = "test multicompany model"

    name = fields.Char()
    company_id = fields.Many2one("res.company")
