from odoo import models
from odoo.tools import populate


class Filter(models.Model):
    _inherit = "ir.filters"

    # Based on the sizes of res.users, 10 filters per user.
    _populate_sizes = {
        'small': 100,
        'medium': 10000,
        'large': 100000,
    }
    _populate_dependencies = ['res.users']

    def _populate_factories(self):
        return [
            ('name', populate.constant('filter_{counter}')),
            ('user_id', populate.randomize(self.env.registry.populated_models['res.users'])),
            ('domain', populate.iterate(["[('id', '=', 1)]", "[('id', '=', 2)]", "[('id', '=', 3)]"])),
            ('context', populate.iterate(["{{}}", "{{'group_by': ['create_date:month']}}"])),
            ('sort', populate.iterate(["[]"])),
            ('model_id', populate.randomize(
                list(dict(self._fields['model_id'].get_description(self.env, ['selection'])['selection']).keys())
            )),
            ('is_default', populate.cartesian([True, False], [0.1, 0.9])),
            ('action_id', populate.randomize(self.env['ir.actions.actions'].search([]).ids)),
        ]
