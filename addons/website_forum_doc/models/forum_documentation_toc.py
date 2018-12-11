# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class Documentation(models.Model):
    _name = 'forum.documentation.toc'
    _description = 'Documentation ToC'
    _inherit = ['website.seo.metadata']
    _order = "sequence, name"
    _parent_order = "sequence, name"
    _parent_store = True

    sequence = fields.Integer('Sequence')
    name = fields.Char('Name', required=True, translate=True)
    introduction = fields.Html('Introduction', translate=True)
    parent_id = fields.Many2one('forum.documentation.toc', string='Parent Table Of Content', ondelete='cascade')
    child_ids = fields.One2many('forum.documentation.toc', 'parent_id', string='Children Table Of Content')
    parent_left = fields.Integer(string='Left Parent', index=True)
    parent_right = fields.Integer(string='Right Parent', index=True)
    post_ids = fields.One2many('forum.post', 'documentation_toc_id', string='Posts')
    forum_id = fields.Many2one('forum.forum', string='Forum', required=True)

    @api.multi
    def name_get(self):
        res = []
        for record in self:
            name = record.name
            if record.parent_id:
                name = record.parent_id.name + ' / ' + name
            res.append((record.id, name))
        return res

    @api.constrains('parent_id')
    def _check_parent_id(self):
        if not self._check_recursion():
            raise ValidationError(_('Error ! You cannot create recursive categories.'))


class DocumentationStage(models.Model):
    _name = 'forum.documentation.stage'
    _description = 'Post Stage'
    _order = 'sequence'

    sequence = fields.Integer('Sequence')
    name = fields.Char(string='Stage Name', required=True, translate=True)
