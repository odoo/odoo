from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    date = fields.Date()  # for test_read_progress_bar
