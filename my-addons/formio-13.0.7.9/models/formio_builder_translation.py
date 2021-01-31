# Copyright Nova Code (http://www.novacode.nl)
# See LICENSE file for full licensing details.

from odoo import api, fields, models, _


class BuilderTranslation(models.Model):
    _name = 'formio.builder.translation'
    _description = 'Formio Builder Translation'
    _order = 'lang_id ASC'

    builder_id = fields.Many2one(
        'formio.builder', string='Form Builder', required=True, ondelete='cascade')
    lang_id = fields.Many2one('res.lang', string='Language', required=True)
    source = fields.Text(string='Source Term', required=True)
    value = fields.Text(string='Translated Value', required=True)

    @api.depends('lang_id', 'source', 'value')
    def name_get(self):
        res = []
        for r in self:
            name = '{lang}: {source} => {value}'.format(
                lang=r.lang_id, source=r.source, value=r.value
            )
            res.append((r.id, name))
        return res
