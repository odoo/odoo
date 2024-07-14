# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, models, fields, api

class DataMergeRule(models.Model):
    _name = 'data_merge.rule'
    _description = 'Deduplication Rule'
    _order = 'sequence, field_id'

    model_id = fields.Many2one('data_merge.model', string='Deduplication Model', ondelete='cascade', required=True)
    res_model_id = fields.Many2one(related='model_id.res_model_id', readonly=True, store=True)
    field_id = fields.Many2one('ir.model.fields', string='Unique ID Field',
        domain="[('model_id', '=', res_model_id), ('ttype', 'in', ('char', 'text', 'many2one')), ('store', '=', True)]",
        required=True, ondelete='cascade')
    match_mode = fields.Selection(
        lambda self: self._available_match_modes(),
        default='exact', string='Merge If', required=True)
    sequence = fields.Integer(string='Sequence', default=1)

    _sql_constraints = [
        ('uniq_model_id_field_id', 'unique(model_id, field_id)', 'A field can only appear once!'),
    ]

    def _available_match_modes(self):
        modes = [('exact', _("Exact Match"))]
        # can't conditionally set demo data...
        if self.env.context.get('install_mode') or self.env.registry.has_unaccent:
            modes.append(('accent', _("Case/Accent Insensitive Match")))
        return modes

    def _update_default_rules(self):
        if self.env.registry.has_unaccent:
            self.match_mode = 'accent'
