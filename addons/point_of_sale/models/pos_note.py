# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _


class PosNote(models.Model):
    _name = 'pos.note'
    _description = 'PoS Note'
    _inherit = ['pos.load.mixin']
    _order = "sequence"

    name = fields.Char(required=True)
    sequence = fields.Integer('Sequence', default=1)
    color = fields.Integer(string='Color')

    _name_unique = models.Constraint(
        'unique (name)',
        'A note with this name already exists',
    )

    def copy_data(self, default=None):
        default = dict(default or {})
        vals_list = super().copy_data(default=default)
        if 'name' not in default:
            for note, vals in zip(self, vals_list):
                vals['name'] = _("%s (copy)", note.name)
        return vals_list

    @api.model
    def _load_pos_data_domain(self, data, config):
        return [('id', 'in', config.note_ids.ids)] if config.note_ids else []

    @api.model
    def _load_pos_data_fields(self, config):
        return ['name', 'color']
