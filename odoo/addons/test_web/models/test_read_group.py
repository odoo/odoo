from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    datetime = fields.Datetime()  # for test_read_progress_bar
