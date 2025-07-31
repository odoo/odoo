from odoo import api, fields, models


class PosCourse(models.Model):
    _name = 'pos.course'
    _description = 'POS Course'
    _inherit = ['pos.load.mixin']
    _order = 'sequence'

    def _default_sequence(self):
        return (self.search([], order="sequence desc", limit=1).sequence or 0) + 1

    name = fields.Char(string="Course Name", required=True)
    sequence = fields.Integer(string="Sequence", default=_default_sequence)
    category_ids = fields.One2many('pos.category', 'course_id', string="Pos Category")

    _name_unique = models.Constraint(
        'unique (name)',
        'A course with this name already exists',
    )

    @api.model
    def _load_pos_data_domain(self, data, config):
        pos_categ = config.iface_available_categ_ids.ids
        available_categ_ids = pos_categ if len(pos_categ) else self.env['pos.category'].search([]).ids
        return [['category_ids', 'in', available_categ_ids]]

    @api.model
    def _load_pos_data_fields(self, config):
        return ['name', 'sequence', 'category_ids']
