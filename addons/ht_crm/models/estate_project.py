from odoo import models, fields, api

class EstateProject(models.Model):
    _name = 'estate.project'
    _description = 'Real Estate Project'

    name = fields.Char(string="Project Name", required=True)
    investor = fields.Char(string="Investor")
    location = fields.Char(string="Location")

    area = fields.Float(string="Area (ha)")
    price_per_m2 = fields.Float(string="Price (VND/m²)")

    legal_status = fields.Selection([
        ('pink_book', 'Pink Book'),
        ('red_book', 'Red Book'),
        ('sale_contract', 'Sale Contract'),
        ('pending', 'Pending')
    ], string="Legal Status")

    progress = fields.Selection([
        ('planning', 'Planning'),
        ('launching', 'Launching Soon'),
        ('under_construction', 'Under Construction'),
        ('completed', 'Completed')
    ], string="Progress")

    note = fields.Text(string="Notes")

    customer_ids = fields.Many2many(
        'sale.customer',
        string="Đang được quan tâm"
    )