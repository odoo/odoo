# -*- coding: utf-8 -*-

from openerp import _, api, fields, models
from openerp.exceptions import ValidationError


class Documentation(models.Model):
    _name = 'forum.documentation.toc'
    _description = 'Documentation ToC'
    _inherit = ['website.seo.metadata']
    _order = "parent_left"
    _parent_order = "sequence, name"
    _parent_store = True

    @api.multi
    def name_get(self):
        res = []
        for record in self:
            name = record.name
            if record.parent_id:
                name = record.parent_id.name+' / '+name
            res.append((record.id, name))
        return res

    sequence = fields.Integer()
    name = fields.Char(required=True, translate=True)
    introduction = fields.Html(translate=True)
    parent_id = fields.Many2one('forum.documentation.toc', string='Parent Table Of Content', ondelete='cascade')
    child_ids = fields.One2many('forum.documentation.toc', 'parent_id', string='Children Table Of Content')
    parent_left = fields.Integer(string='Left Parent', select=True)
    parent_right = fields.Integer(string='Right Parent', select=True)
    post_ids = fields.One2many('forum.post', 'documentation_toc_id', string='Posts')
    forum_id = fields.Many2one('forum.forum', string='Forum', required=True)

    @api.one
    @api.constrains('parent_id')
    def _check_parent_id(self):
        if not self._check_recursion():
            raise ValidationError(_('Error ! You cannot create recursive categories.'))

class DocumentationStage(models.Model):
    _name = 'forum.documentation.stage'
    _description = 'Post Stage'
    _order = 'sequence'

    sequence = fields.Integer()
    name = fields.Char(string='Stage Name', required=True, translate=True)


class Post(models.Model):
    _inherit = 'forum.post'

    @api.multi
    def _get_default_stage_id(self):
        return self.env["forum.documentation.stage"].search([], limit=1)

    documentation_toc_id = fields.Many2one('forum.documentation.toc', string='Documentation ToC', ondelete='set null')
    documentation_stage_id = fields.Many2one('forum.documentation.stage', string='Documentation Stage', default=_get_default_stage_id)
    color = fields.Integer(string='Color Index')

    @api.multi
    def _read_group_stage_ids(self, domain, read_group_order=None, access_rights_uid=None):
        return self.env['forum.documentation.stage'].search([]).name_get(), {}

    _group_by_full = {
        'documentation_stage_id': _read_group_stage_ids,
    }
