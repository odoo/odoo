from odoo import fields, models, api


class PosCategory(models.Model):
    _inherit = 'pos.category'

    course_id = fields.Many2one('pos.course', string="Course", index=True)

    @api.model
    def _load_pos_data_fields(self, config):
        return super()._load_pos_data_fields(config) + ['course_id']
