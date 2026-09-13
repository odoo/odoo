from odoo import api, fields, models


class PosOrderLine(models.Model):
    _inherit = "pos.order.line"
    course_id = fields.Many2one(
        comodel_name="restaurant.order.course",
        string="Course Ref",
        index="btree_not_null",
        ondelete="set null",
    )

    @api.model
    def _load_pos_data_fields(self, config):
        result = super()._load_pos_data_fields(config)
        return result + ["course_id"]
