from odoo import fields, models


class TestReadGroupPartner(models.Model):
    _inherit = 'test_read_group.partner'

    datetime = fields.Datetime()  # for test_read_progress_bar
