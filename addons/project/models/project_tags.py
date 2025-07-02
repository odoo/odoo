# Part of Odoo. See LICENSE file for full copyright and licensing details.

from random import randint

from odoo import api, fields, models
from odoo.fields import Domain
from odoo.tools import SQL


class ProjectTags(models.Model):
    """ Tags of project's tasks """
    _name = 'project.tags'
    _description = "Project Tags"
    _order = "name"

    def _get_default_color(self):
        return randint(1, 11)

    name = fields.Char('Name', required=True, translate=True)
    color = fields.Integer(string='Color', default=_get_default_color,
        help="Transparent tags are not visible in the kanban view of your projects and tasks.")
    project_ids = fields.Many2many('project.project', 'project_project_project_tags_rel', string='Projects', export_string_translation=False)
    task_ids = fields.Many2many('project.task', string='Tasks', export_string_translation=False)

    _name_uniq = models.Constraint(
        'unique (name)',
        'A tag with the same name already exists.',
    )

    def _get_project_tags_domain(self, domain, project_id):
        # TODO: Remove in master
        return domain

    @api.model
    def formatted_read_group(self, domain, groupby=(), aggregates=(), having=(), offset=0, limit=None, order=None) -> list[dict]:
        if 'project_id' in self.env.context:
            tag_ids = [id_ for id_, _label in self.name_search()]
            domain = Domain.AND([domain, [('id', 'in', tag_ids)]])
        return super().formatted_read_group(domain, groupby, aggregates, having=having, offset=offset, limit=limit, order=order)

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        if 'project_id' in self.env.context:
            tag_ids = [id_ for id_, _label in self.name_search()]
            domain = Domain.AND([domain, [('id', 'in', tag_ids)]])
            return self.arrange_tag_list_by_id(super().search_read(domain=domain, fields=fields, offset=offset, limit=limit), tag_ids)
        return super().search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)

    @api.model
    def arrange_tag_list_by_id(self, tag_list, id_order):
        """arrange_tag_list_by_id re-order a list of record values (dict) following a given id sequence
           complexity: O(n)
           param:
                - tag_list: ordered (by id) list of record values, each record being a dict
                  containing at least an 'id' key
                - id_order: list of value (int) corresponding to the id of the records to re-arrange
           result:
                - Sorted list of record values (dict)
        """
        tags_by_id = {tag['id']: tag for tag in tag_list}
        return [tags_by_id[id] for id in id_order if id in tags_by_id]

    @api.model
    def name_search(self, name='', domain=None, operator='ilike', limit=100):
        if limit is None:
            return super().name_search(name, domain, operator, limit)
        tags = self.browse()
        domain = Domain.AND([self._search_display_name(operator, name), domain or Domain.TRUE])
        if self.env.context.get('project_id'):
            # optimisation for large projects, we look first for tags present on the last 1000 tasks of said project.
            # when not enough results are found, we complete them with a fallback on a regular search
            tag_sql = SQL("""
                (SELECT DISTINCT project_tasks_tags.id
                FROM (
                    SELECT rel.project_tags_id AS id
                    FROM project_tags_project_task_rel AS rel
                    JOIN project_task AS task
                        ON task.id=rel.project_task_id
                        AND task.project_id=%(project_id)s
                    ORDER BY task.id DESC
                    LIMIT 1000
                ) AS project_tasks_tags
            )""", project_id=self.env.context['project_id'])
            tags += self.search_fetch(Domain('id', 'in', tag_sql) & domain, ['display_name'], limit=limit)
        if len(tags) < limit:
            tags += self.search_fetch(Domain('id', 'not in', tags.ids) & domain, ['display_name'], limit=limit - len(tags))
        return [(tag.id, tag.display_name) for tag in tags.sudo()]

    @api.model
    def name_create(self, name):
        existing_tag = self.search([('name', '=ilike', name.strip())], limit=1)
        if existing_tag:
            return existing_tag.id, existing_tag.display_name
        return super().name_create(name)
