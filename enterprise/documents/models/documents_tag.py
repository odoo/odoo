# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from random import randint

from odoo import _, api, models, fields
from odoo.exceptions import UserError


class Tags(models.Model):
    _name = "documents.tag"
    _description = "Tag"
    _order = "sequence, name"

    @api.model
    def _get_default_color(self):
        return randint(1, 11)

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer('Sequence', default=10)
    color = fields.Integer('Color', default=_get_default_color)
    tooltip = fields.Char(help="Text shown when hovering on this tag", string="Tooltip")  # Deprecated
    document_ids = fields.Many2many('documents.document', 'document_tag_rel')

    _sql_constraints = [
        ('tag_name_unique', 'unique (name)', "Tag name already used"),
    ]

    # todo: unused, remove in master
    @api.model
    def _get_tags(self, domain):
        """
        fetches the tag and facet ids for the document selector (custom left sidebar of the kanban view)
        """
        tags = self.env['documents.document'].search(domain).tag_ids
        return [
            {
                'sequence': tag.sequence,
                'id': tag.id,
                'color': tag.color,
                '__count': len(tag.document_ids)
            } for tag in tags
        ]

    @api.ondelete(at_uninstall=False)
    def _unlink_except_used_in_server_action(self):
        external_ids = self._get_external_ids()
        resource_refs = [f'documents.tag,{k}' for k in external_ids.keys()]
        if external_ids and self.env['ir.actions.server'].search_count([('resource_ref', 'in', resource_refs)], limit=1):
            raise UserError(_("You cannot delete tags used in server actions."))
