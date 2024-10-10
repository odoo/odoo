from odoo import models, fields


class TestModel_Multicompany(models.Model):
    _description = "test multicompany model"

    name = fields.Char()
    company_id = fields.Many2one("res.company")
