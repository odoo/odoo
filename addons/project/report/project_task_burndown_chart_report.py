# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.models import regex_field_agg, VALID_AGGREGATE_FUNCTIONS
from odoo.exceptions import UserError
from odoo.osv.expression import AND_OPERATOR, OR_OPERATOR, NOT_OPERATOR, DOMAIN_OPERATORS, FALSE_LEAF, TRUE_LEAF, normalize_domain
from odoo.tools import OrderedSet


def remove_domain_leaf(domain, fields_to_remove):
    """ Make the provided domain insensitive to the fields provided in fields_to_remove. Fields that are part of
    `fields_to_remove` are replaced by either a `FALSE_LEAF` or a `TRUE_LEAF` in order to ensure the evaluation of the
    complete domain.

    :param domain: The domain to process.
    :param fields_to_remove: List of fields the domain has to be insensitive to.
    :return: The insensitive domain.
    """
    def _process_leaf(elements, index, operator, new_domain):
        leaf = elements[index]
        if len(leaf) == 3:
            if leaf[0] in fields_to_remove:
                if operator == AND_OPERATOR:
                    new_domain.append(TRUE_LEAF)
                elif operator == OR_OPERATOR:
                    new_domain.append(FALSE_LEAF)
            else:
                new_domain.append(leaf)
            return 1
        elif len(leaf) == 1 and leaf in DOMAIN_OPERATORS:
            # Special case to avoid OR ('|') that can never resolve to true
            if leaf == OR_OPERATOR \
                    and len(elements[index + 1]) == 3 and len(elements[index + 2]) == 3 \
                    and elements[index + 1][0] in fields_to_remove and elements[index + 1][0] in fields_to_remove:
                new_domain.append(TRUE_LEAF)
                return 3
            new_domain.append(leaf)
            if leaf[0] == NOT_OPERATOR:
                return 1 + _process_leaf(elements, index + 1, '&', new_domain)
            first_leaf_skip = _process_leaf(elements, index + 1, leaf, new_domain)
            second_leaf_skip = _process_leaf(elements, index + 1 + first_leaf_skip, leaf, new_domain)
            return 1 + first_leaf_skip + second_leaf_skip
        return 0

    if len(domain) == 0:
        return domain
    new_domain = []
    _process_leaf(normalize_domain(domain), 0, AND_OPERATOR, new_domain)
    return new_domain


class ReportProjectTaskBurndownChart(models.AbstractModel):
    _name = 'project.task.burndown.chart.report'
    _description = 'Burndown Chart'
    _auto = False
    _order = 'date'

    planned_hours = fields.Float(string='Allocated Hours', readonly=True)
    date = fields.Datetime('Date', readonly=True)
    date_assign = fields.Datetime(string='Assignment Date', readonly=True)
    date_deadline = fields.Date(string='Deadline', readonly=True)
    display_project_id = fields.Many2one('project.project', readonly=True)
    is_closed = fields.Boolean("Closing Stage", readonly=True)
    milestone_id = fields.Many2one('project.milestone', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Customer', readonly=True)
    project_id = fields.Many2one('project.project', readonly=True)
    stage_id = fields.Many2one('project.task.type', readonly=True)
    user_ids = fields.Many2many('res.users', relation='project_task_user_rel', column1='task_id', column2='user_id',
                                string='Assignees', readonly=True)

    # Fake field required as used in the filters. It will however be managed through the `project.task` model.
    has_late_and_unreached_milestone = fields.Boolean(readonly=True)

    # This variable is used in order to distinguish conditions that can be set on `project.task` and thus being used
    # at a lower level than the "usual" query made by the `read_group_raw`. Indeed, the domain applied on those fields
    # will be performed on a `CTE` that will be later use in the `SQL` in order to limit the subset of data that is used
    # in the successive `GROUP BY` statements.
    task_specific_fields = [
        'date_assign',
        'date_deadline',
        'display_project_id',
        'has_late_and_unreached_milestone',
        'is_closed',
        'milestone_id',
        'partner_id',
        'project_id',
        'stage_id',
        'user_ids',
    ]

    def _get_group_by_SQL(self, task_specific_domain, count_field, select_terms, from_clause, where_clause,
                          where_clause_params, groupby_terms, orderby_terms, limit, offset, groupby, annotated_groupbys,
                          prefix_term, prefix_terms):
        """ Prepare and return the SQL to be used for the read_group. """

        # Build the query on `project.task` with the domain fields that are linked to that model. This is done in order
        # to be able to reduce the number of treated records in the query by limiting them to the one corresponding to
        # the ids that are returned from this sub query.
        project_task_query = self.env['project.task']._where_calc(task_specific_domain)
        project_task_from_clause, project_task_where_clause, project_task_where_clause_params = project_task_query.get_sql()

        # Get the stage_id `ir.model.fields`'s id in order to inject it directly in the query and avoid having to join
        # on `ir_model_fields` table.
        IrModelFieldsSudo = self.env['ir.model.fields'].sudo()
        field_id = IrModelFieldsSudo.search([('name', '=', 'stage_id'), ('model', '=', 'project.task')]).id

        # Get the date aggregation SQL statement in order to be able to inject it in the SQL.
        date_group_by_field = next(filter(lambda gb: gb.startswith('date'), groupby))
        date_annotated_groupby = [
            annotated_groupby for annotated_groupby in annotated_groupbys
            if annotated_groupby['groupby'] == date_group_by_field
        ][0]
        date_begin, date_end = (
            date_annotated_groupby['qualified_field'].replace(
                '"%s"."%s"' % (self._table, date_annotated_groupby['field']), '"%s_%s"' % (date_annotated_groupby['field'], field)
            )
            for field in ['begin', 'end']
        )

        # Insert `WHERE` clause parameter that apply on `project_task` prior to the one that apply on
        # `project_task_burndown_chart_report` as the `project_task` CTE is placed at the beginning of the `SQL`.
        for param in reversed(project_task_where_clause_params):
            where_clause_params.insert(0, param)

        # Computes the interval which needs to be used in the `SQL` depending on the date group by interval.
        if date_annotated_groupby['groupby'].split(':')[1] != 'quarter':
            interval = '1 %s' % date_annotated_groupby['groupby'].split(':')[1]
        else:
            interval = '3 month'

        burndown_chart_query = """
              WITH task_ids AS (
                 SELECT id
                 FROM %(task_query_from)s
                 %(task_query_where)s
              ),
              all_stage_task_moves AS (
                 SELECT count(*) as %(count_field)s,
                        sum(planned_hours) as planned_hours,
                        project_id,
                        display_project_id,
                        %(date_begin)s as date_begin,
                        %(date_end)s as date_end,
                        stage_id
                   FROM (
                            -- Gathers the stage_ids history per task_id. This query gets:
                            -- * All changes except the last one for those for which we have at least a mail
                            --   message and a mail tracking value on project.task stage_id.
                            -- * The stage at creation for those for which we do not have any mail message and a
                            --   mail tracking value on project.task stage_id.
                            SELECT DISTINCT task_id,
                                   planned_hours,
                                   project_id,
                                   display_project_id,
                                   %(date_begin)s as date_begin,
                                   %(date_end)s as date_end,
                                   first_value(stage_id) OVER task_date_begin_window AS stage_id
                              FROM (
                                     SELECT pt.id as task_id,
                                            pt.planned_hours,
                                            pt.project_id,
                                            pt.display_project_id,
                                            COALESCE(LAG(mm.date) OVER (PARTITION BY mm.res_id ORDER BY mm.id), pt.create_date) as date_begin,
                                            CASE WHEN mtv.id IS NOT NULL THEN mm.date
                                                ELSE (now() at time zone 'utc')::date + INTERVAL '%(interval)s'
                                            END as date_end,
                                            CASE WHEN mtv.id IS NOT NULL THEN mtv.old_value_integer
                                               ELSE pt.stage_id
                                            END as stage_id
                                       FROM project_task pt
                                                LEFT JOIN (
                                                    mail_message mm
                                                        JOIN mail_tracking_value mtv ON mm.id = mtv.mail_message_id
                                                                                     AND mtv.field = %(field_id)s
                                                                                     AND mm.model='project.task'
                                                                                     AND mm.message_type = 'notification'
                                                        JOIN project_task_type ptt ON ptt.id = mtv.old_value_integer
                                                ) ON mm.res_id = pt.id
                                      WHERE pt.active=true AND pt.id IN (SELECT id from task_ids)
                                   ) task_stage_id_history
                          GROUP BY task_id,
                                   planned_hours,
                                   project_id,
                                   display_project_id,
                                   %(date_begin)s,
                                   %(date_end)s,
                                   stage_id
                            WINDOW task_date_begin_window AS (PARTITION BY task_id, %(date_begin)s)
                          UNION ALL
                            -- Gathers the current stage_ids per task_id for those which values changed at least
                            -- once (=those for which we have at least a mail message and a mail tracking value
                            -- on project.task stage_id).
                            SELECT pt.id as task_id,
                                   pt.planned_hours,
                                   pt.project_id,
                                   pt.display_project_id,
                                   last_stage_id_change_mail_message.date as date_begin,
                                   (now() at time zone 'utc')::date + INTERVAL '%(interval)s' as date_end,
                                   pt.stage_id as old_value_integer
                              FROM project_task pt
                                   JOIN project_task_type ptt ON ptt.id = pt.stage_id
                                   JOIN LATERAL (
                                       SELECT mm.date
                                       FROM mail_message mm
                                       JOIN mail_tracking_value mtv ON mm.id = mtv.mail_message_id
                                       AND mtv.field = %(field_id)s
                                       AND mm.model='project.task'
                                       AND mm.message_type = 'notification'
                                       AND mm.res_id = pt.id
                                       ORDER BY mm.id DESC
                                       FETCH FIRST ROW ONLY
                                   ) AS last_stage_id_change_mail_message ON TRUE
                             WHERE pt.active=true AND pt.id IN (SELECT id from task_ids)
                        ) AS project_task_burndown_chart
               GROUP BY planned_hours,
                        project_id,
                        display_project_id,
                        %(date_begin)s,
                        %(date_end)s,
                        stage_id
              )
              SELECT (project_id*10^13 + stage_id*10^7 + to_char(date, 'YYMMDD')::integer)::bigint as id,
                     planned_hours,
                     project_id,
                     display_project_id,
                     stage_id,
                     date,
                     %(count_field)s
                FROM all_stage_task_moves t
                         JOIN LATERAL generate_series(t.date_begin, t.date_end-INTERVAL '1 day', '%(interval)s')
                            AS date ON TRUE
        """ % {
            'task_query_from': project_task_from_clause,
            'task_query_where': prefix_term('WHERE', project_task_where_clause),
            'count_field': count_field,
            'date_begin': date_begin,
            'date_end': date_end,
            'interval': interval,
            'field_id': field_id,
        }

        # Replace, in the `FROM` clause generated on `project_task_burndown_chart_report`, the
        # `project_task_burndown_chart_report` table name by the burndown_chart_query `SQL` aliased as
        # `project_task_burndown_chart_report`.
        from_clause = from_clause.replace('"project_task_burndown_chart_report"', '(%s) AS "project_task_burndown_chart_report"' % burndown_chart_query, 1)

        return """
            SELECT min("%(table)s".id) AS id, sum(%(table)s.%(count_field)s) AS "%(count_field)s" %(extra_fields)s
            FROM %(from)s
            %(where)s
            %(groupby)s
            %(orderby)s
            %(limit)s
            %(offset)s
        """ % {
            'table': self._table,
            'count_field': count_field,
            'extra_fields': prefix_terms(',', select_terms),
            'from': from_clause,
            'where': prefix_term('WHERE', where_clause),
            'groupby': prefix_terms('GROUP BY', groupby_terms),
            'orderby': prefix_terms('ORDER BY', orderby_terms),
            'limit': prefix_term('LIMIT', int(limit) if limit else None),
            'offset': prefix_term('OFFSET', int(offset) if limit else None),
        }

    @api.model
    def _validate_group_by(self, groupby):
        """ Check that the both `date` and `stage_id` are part of `group_by`, otherwise raise a `UserError`.

        :param groupby: List of group by fields.
        """
        stage_id_in_groupby = False
        date_in_groupby = False

        for gb in groupby:
            if gb.startswith('date'):
                date_in_groupby = True
            else:
                if gb == 'stage_id':
                    stage_id_in_groupby = True

        if not date_in_groupby or not stage_id_in_groupby:
            raise UserError(_('The view must be grouped by date and by stage_id'))

    @api.model
    def _determine_domains(self, domain):
        """ Compute two separated domain from the provided one:
        * A domain that only contains fields that are specific to `project.task.burndown.chart.report`
        * A domain that only contains fields that are specific to `project.task`

        Fields that are not part of the constraint are replaced by either a `FALSE_LEAF` or a `TRUE_LEAF` in order
        to ensure the complete domain evaluation. See `remove_domain_leaf` for more details.

        :param domain: The domain that has been passed to the read_group.
        :return: A tuple containing the non `project.task` specific domain and the `project.task` specific domain.
        """
        burndown_chart_specific_fields = list(set(self._fields) - set(self.task_specific_fields))
        task_specific_domain = remove_domain_leaf(domain, burndown_chart_specific_fields)
        non_task_specific_domain = remove_domain_leaf(domain, self.task_specific_fields)
        return non_task_specific_domain, task_specific_domain

    @api.model
    def _read_group_raw(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        """ Although not being a good practice, this code is, for a big part, duplicated from `read_group_raw` from
        `models.py`. In order to be able to use the report on big databases, it is necessary to inject `WHERE`
        statements at the lowest levels in the report `SQL`. As a result, using a view was no more an option as
        `Postgres` could not optimise the `SQL`.
        The code of `fill_temporal` has been removed from what's available in `models.py` as it is not relevant in the
        context of the Burndown Chart. Indeed, series are generated so no empty are returned by the `SQL`, except if
        explicitly specified in the domain through the `date` field, which is then expected.
        """

        # --- Below code is custom

        self._validate_group_by(groupby)
        burndown_specific_domain, task_specific_domain = self._determine_domains(domain)

        # --- Below code is from models.py read_group_raw

        self.check_access_rights('read')
        query = self._where_calc(burndown_specific_domain)
        fields = fields or [f.name for f in self._fields.values() if f.store]

        groupby = [groupby] if isinstance(groupby, str) else list(OrderedSet(groupby))
        groupby_list = groupby[:1] if lazy else groupby
        annotated_groupbys = [self._read_group_process_groupby(gb, query) for gb in groupby_list]
        groupby_fields = [g['field'] for g in annotated_groupbys]
        order = orderby or ','.join([g for g in groupby_list])
        groupby_dict = {gb['groupby']: gb for gb in annotated_groupbys}

        self._apply_ir_rules(query, 'read')
        for gb in groupby_fields:
            if gb not in self._fields:
                raise UserError(_("Unknown field %r in 'groupby'", gb))
            if not self._fields[gb].base_field.groupable:
                raise UserError(_(
                    "Field %s is not a stored field, only stored fields (regular or "
                    "many2many) are valid for the 'groupby' parameter", self._fields[gb],
                ))

        aggregated_fields = []
        select_terms = []
        fnames = []                     # list of fields to flush

        for fspec in fields:
            if fspec == 'sequence':
                continue
            if fspec == '__count':
                # the web client sometimes adds this pseudo-field in the list
                continue

            match = regex_field_agg.match(fspec)
            if not match:
                raise UserError(_("Invalid field specification %r.", fspec))

            name, func, fname = match.groups()
            if func:
                # we have either 'name:func' or 'name:func(fname)'
                fname = fname or name
                field = self._fields.get(fname)
                if not field:
                    raise ValueError(_("Invalid field %r on model %r", (fname, self._name)))
                if not (field.base_field.store and field.base_field.column_type):
                    raise UserError(_("Cannot aggregate field %r.", fname))
                if func not in VALID_AGGREGATE_FUNCTIONS:
                    raise UserError(_("Invalid aggregation function %r.", func))
            else:
                # we have 'name', retrieve the aggregator on the field
                field = self._fields.get(name)
                if not field:
                    raise ValueError(_("Invalid field %r on model %r", (name, self._name)))
                if not (field.base_field.store and
                        field.base_field.column_type and field.group_operator):
                    continue
                func, fname = field.group_operator, name

            fnames.append(fname)

            if fname in groupby_fields:
                continue
            if name in aggregated_fields:
                raise UserError(_("Output name %r is used twice.", name))
            aggregated_fields.append(name)

            expr = self._inherits_join_calc(self._table, fname, query)
            if func.lower() == 'count_distinct':
                term = 'COUNT(DISTINCT %s) AS "%s"' % (expr, name)
            else:
                term = '%s(%s) AS "%s"' % (func, expr, name)
            select_terms.append(term)

        for gb in annotated_groupbys:
            select_terms.append('%s as "%s" ' % (gb['qualified_field'], gb['groupby']))

        # --- Below code is custom
        # --- As the report is base on `project.task` we flush that specific model

        # self._flush_search(domain, fields=fnames + groupby_fields)
        self.env['project.task']._flush_search(task_specific_domain, fields=self.task_specific_fields)

        # --- Below code is from models.py read_group_raw

        groupby_terms, orderby_terms = self._read_group_prepare(order, aggregated_fields, annotated_groupbys, query)
        from_clause, where_clause, where_clause_params = query.get_sql()
        if lazy and (len(groupby_fields) >= 2 or not self._context.get('group_by_no_leaf')):
            count_field = groupby_fields[0] if len(groupby_fields) >= 1 else '_'
        else:
            count_field = '_'
        count_field += '_count'

        prefix_terms = lambda prefix, terms: (prefix + " " + ",".join(terms)) if terms else ''
        prefix_term = lambda prefix, term: ('%s %s' % (prefix, term)) if term else ''

        # --- Below code is custom

        query = self._get_group_by_SQL(task_specific_domain, count_field, select_terms, from_clause, where_clause,
                                       where_clause_params, groupby_terms, orderby_terms, limit, offset, groupby,
                                       annotated_groupbys, prefix_term, prefix_terms)

        # --- Below code is from models.py read_group_raw

        self._cr.execute(query, where_clause_params)
        fetched_data = self._cr.dictfetchall()

        if not groupby_fields:
            return fetched_data

        self._read_group_resolve_many2x_fields(fetched_data, annotated_groupbys)

        data = [{k: self._read_group_prepare_data(k, v, groupby_dict) for k, v in r.items()} for r in fetched_data]

        result = [self._read_group_format_result(d, annotated_groupbys, groupby, domain) for d in data]

        # --- Below code is custom
        # --- We removed fill_temporal handling as not relevant in the context of the Burndown Chart

        # --- Below code is from models.py read_group_raw

        if lazy:
            # Right now, read_group only fill results in lazy mode (by default).
            # If you need to have the empty groups in 'eager' mode, then the
            # method _read_group_fill_results need to be completely reimplemented
            # in a sane way
            result = self._read_group_fill_results(
                domain, groupby_fields[0], groupby[len(annotated_groupbys):],
                aggregated_fields, count_field, result, read_group_order=order,
            )
        return result
