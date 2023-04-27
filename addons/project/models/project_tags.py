# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from random import randint

from odoo import api, fields, models, SUPERUSER_ID
from odoo.osv import expression


class ProjectTags(models.Model):
    """ Tags of project's tasks """
    _name = "project.tags"
    _description = "Project Tags"
    _order = "name"

    def _get_default_color(self):
        return randint(1, 11)

    name = fields.Char('Name', required=True, translate=True)
    color = fields.Integer(string='Color', default=_get_default_color,
        help="Transparent tags are not visible in the kanban view of your projects and tasks.")
    project_ids = fields.Many2many('project.project', 'project_project_project_tags_rel', string='Projects')
    task_ids = fields.Many2many('project.task', string='Tasks')

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "A tag with the same name already exists."),
    ]

    def _get_project_tags_domain(self, domain, project_id):
        # TODO: Remove in master
        return domain

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        if 'project_id' in self.env.context:
            tag_ids = self._name_search('')
            domain = expression.AND([domain, [('id', 'in', tag_ids)]])
        return super().read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        if 'project_id' in self.env.context:
            tag_ids = self._name_search('')
            domain = expression.AND([domain, [('id', 'in', tag_ids)]])
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
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        if self.env.context.get('project_id') and operator == 'ilike':
            # `domain` has the form of the default filter ['!', ['id', 'in', <ids>]]
            # passed to exclude already selected tags -> exclude them in our query too
            excluded_ids = list(domain[1][2]) \
                if domain and len(domain) == 2 and domain[0] == '!' and len(domain[1]) == 3 and domain[1][:2] == ["id", "in"] \
                else []
            # UNION ALL is lazy evaluated, if the first query has enough results,
            # the second is not executed (just planned).
            query = """
                WITH query_tags_in_tasks AS (
                    SELECT tags.id, COALESCE(tags.name ->> %(lang)s, tags.name ->> 'en_US') AS name, 1 AS sequence
                    FROM project_tags AS tags
                    JOIN (
                        SELECT project_tags_id
                        FROM project_tags_project_task_rel AS rel
                        JOIN project_task AS task
                            ON task.project_id = %(project_id)s
                            AND task.id = rel.project_task_id
                        ORDER BY task.id DESC
                        LIMIT 1000 -- arbitrary limit to speed up lookup on huge projects (fallback below on global scope)
                    ) AS tags__tasks_ids
                        ON tags__tasks_ids.project_tags_id = tags.id
                    WHERE tags.id != ALL(%(excluded_ids)s)
                    AND COALESCE(tags.name ->> %(lang)s, tags.name ->> 'en_US') ILIKE %(search_term)s
                    GROUP BY 1, 2, 3  -- faster than a distinct
                    LIMIT %(limit)s
                ), query_all_tags AS (
                    SELECT tags.id, COALESCE(tags.name ->> %(lang)s, tags.name ->> 'en_US') AS name, 2 AS sequence
                    FROM project_tags AS tags
                    WHERE tags.id != ALL(%(excluded_ids)s)
                    AND tags.id NOT IN (SELECT id FROM query_tags_in_tasks)
                    AND COALESCE(tags.name ->> %(lang)s, tags.name ->> 'en_US') ILIKE %(search_term)s
                    LIMIT %(limit)s
                )
                SELECT id FROM (
                    SELECT id, name, sequence
                    FROM query_tags_in_tasks
                    UNION ALL
                    SELECT id, name, sequence
                    FROM query_all_tags
                    LIMIT %(limit)s
                ) AS tags
                ORDER BY sequence, name
            """
            params = {
                'project_id': self.env.context.get('project_id'),
                'excluded_ids': excluded_ids,
                'limit': limit,
                'lang': self.env.context.get('lang', 'en_US'),
                'search_term': '%' + name + '%',
            }
            self.env.cr.execute(query, params)
            return [row[0] for row in self.env.cr.fetchall()]
        else:
            return super()._name_search(name, domain, operator, limit, order)

    @api.model
    def name_create(self, name):
        existing_tag = self.search([('name', '=ilike', name.strip())], limit=1)
        if existing_tag:
            return existing_tag.id, existing_tag.display_name
        return super().name_create(name)
