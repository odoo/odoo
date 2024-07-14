# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, fields, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import SQL

from psycopg2 import ProgrammingError, errorcodes

from dateutil.relativedelta import relativedelta

import ast
import timeit
import logging
import re

from odoo.osv.expression import get_unaccent_wrapper

_logger = logging.getLogger(__name__)

# Merge list of list based on their common element
#   Input: [['a', 'b'], ['b', 'c'], ['d', 'e']]
#   Output: [['a', 'b', 'c'], ['d', 'e']]
# https://stackoverflow.com/a/9112588
def merge_common_lists(lsts):
    sets = [set(lst) for lst in lsts if lst]
    merged = True
    while merged:
        merged = False
        results = []
        while sets:
            common, rest = sets[0], sets[1:]
            sets = []
            for x in rest:
                if x.isdisjoint(common):
                    sets.append(x)
                else:
                    merged = True
                    common |= x
            results.append(common)
        sets = results
    return sets


class DataMergeModel(models.Model):
    _name = 'data_merge.model'
    _description = 'Deduplication Model'
    _order = 'name'

    name = fields.Char(string='Name', readonly=False, store=True, required=True, copy=False, compute='_compute_name')
    active = fields.Boolean(default=True)

    res_model_id = fields.Many2one('ir.model', string='Model', required=True, ondelete='cascade')
    res_model_name = fields.Char(related='res_model_id.model', string='Model Name', readonly=True, store=True)
    domain = fields.Char(string='Domain', help='Records eligible for the deduplication process')
    removal_mode = fields.Selection([
        ('archive', 'Archive'),
        ('delete', 'Delete')], string='Duplicate Removal', default='archive')
    merge_mode = fields.Selection([
        ('manual', 'Manual'),
        ('automatic', 'Automatic')], string='Merge Mode', default='manual')
    custom_merge_method = fields.Boolean(compute='_compute_custom_merge_method')

    rule_ids = fields.One2many('data_merge.rule', 'model_id', string="Deduplication Rules", help='Suggest to merge records matching at least one of these rules')
    records_to_merge_count = fields.Integer(compute='_compute_records_to_merge_count')

    mix_by_company = fields.Boolean('Cross-Company', default=False, help="When enabled, duplicates across different companies will be suggested")

    ### User Notifications for Manual merge
    notify_user_ids = fields.Many2many('res.users', string='Notify Users',
        help='List of users to notify when there are new records to merge',
        domain=lambda self: [('groups_id', 'in', self.env.ref('base.group_system').id)])
    notify_frequency = fields.Integer(string='Notify', default=1)
    notify_frequency_period = fields.Selection([
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months')], string='Notify Frequency Period', default='weeks')
    last_notification = fields.Datetime(readonly=True)

    ### Similarity Threshold for Automatic merge
    merge_threshold = fields.Integer(string='Similarity Threshold', default=75, help='Records with a similarity percentage above this threshold will be automatically merged')
    create_threshold = fields.Integer(string='Suggestion Threshold', default=0, help='Duplicates with a similarity below this threshold will not be suggested', groups='base.group_no_one')

    ### Contextual menu action
    is_contextual_merge_action = fields.Boolean(string='Merge action attached', help='If True, this record is used for contextual menu action "Merge" on the target model.')

    _sql_constraints = [
        ('uniq_name', 'UNIQUE(name)', 'This name is already taken'),
        ('check_notif_freq', 'CHECK(notify_frequency > 0)', 'The notification frequency should be greater than 0'),
    ]

    @api.depends('res_model_id')
    def _compute_name(self):
        for dm_model in self:
            dm_model.name = dm_model.res_model_id.name if dm_model.res_model_id else ''

    @api.onchange('res_model_id')
    def _onchange_res_model_id(self):
        self._check_prevent_merge()
        if any(rule.field_id.model_id != self.res_model_id for rule in self.rule_ids):
            self.rule_ids = [(5, 0, 0)]

    def _compute_records_to_merge_count(self):
        count_data = self.env['data_merge.record'].with_context(data_merge_model_ids=tuple(self.ids))._read_group([('model_id', 'in', self.ids)], ['model_id'], ['__count'])
        counts = {model.id: count for model, count in count_data}
        for dm_model in self:
            dm_model.records_to_merge_count = counts[dm_model.id] if dm_model.id in counts else 0

    @api.onchange('res_model_name')
    def _compute_custom_merge_method(self):
        for dm_model in self:
            if dm_model.res_model_name:
                dm_model.custom_merge_method = hasattr(self.env[dm_model.res_model_name], '_merge_method')
            else:
                dm_model.custom_merge_method = False

    ############################
    ### Cron / find duplicates
    ############################
    def _notify_new_duplicates(self):
        """
        Notify the configured users when new duplicate records are found.
        The method is called after the identification process and will notify based on the configured frequency.
        """
        for dm_model in self.env['data_merge.model'].search([('merge_mode', '=', 'manual')]):
            if not dm_model.notify_user_ids or not dm_model.notify_frequency:
                continue

            if dm_model.notify_frequency_period == 'days':
                delta = relativedelta(day=dm_model.notify_frequency)
            elif dm_model.notify_frequency_period == 'weeks':
                delta = relativedelta(weeks=dm_model.notify_frequency)
            else:
                delta = relativedelta(months=dm_model.notify_frequency)

            if not dm_model.last_notification or (dm_model.last_notification + delta) < fields.Datetime.now():
                dm_model.last_notification = fields.Datetime.now()
                dm_model._send_notification(delta)

    def _send_notification(self, delta):
        """
        Send a notification to the users if there are duplicates created since today minus `delta`

        :param delta: delta representing the notification frequency
        """
        self.ensure_one()
        last_date = fields.Date.today() - delta
        num_records = self.env['data_merge.record'].search_count([
            ('model_id', '=', self.id),
            ('create_date', '>=', last_date),
        ])
        if num_records:
            partner_ids = self.notify_user_ids.partner_id.ids
            menu_id = self.env.ref('data_recycle.menu_data_cleaning_root').id
            self.env['mail.thread'].sudo().message_notify(
                body=self.env['ir.qweb']._render(
                    'data_merge.data_merge_duplicate',
                    dict(
                        num_records=num_records,
                        res_model_label=self.res_model_id.name,
                        model_id=self.id,
                        menu_id=menu_id
                    )
                ),
                model=self._name,
                notify_author=True,
                partner_ids=partner_ids,
                res_id=self.id,
                subject=_('Duplicates to Merge'),
            )

    def _cron_find_duplicates(self):
        """
        Identify duplicate records for each active model and either notify the users or automatically merge the duplicates
        """
        self.env['data_merge.model'].sudo().search([]).find_duplicates(batch_commits=True)
        self._notify_new_duplicates()

    def find_duplicates(self, batch_commits=False):
        """
        Search for duplicate records and create the data_merge.group along with its data_merge.record

        :param bool batch_commits: If set, will automatically commit every X records
        """
        unaccent = get_unaccent_wrapper(self.env.cr)
        self.env.flush_all()
        for dm_model in self:
            t1 = timeit.default_timer()
            ids = []
            res_model = self.env[dm_model.res_model_name]
            table = res_model._table

            for rule in dm_model.rule_ids:
                domain = ast.literal_eval(dm_model.domain or '[]')
                query = res_model._where_calc(domain)
                sql_field = res_model._field_to_sql(table, rule.field_id.name, query)
                if rule.field_id.relation:
                    related_model = self.env[rule.field_id.relation]
                    lhs_alias, lhs_column = re.findall(r'"([^"]+)"', sql_field.code)
                    rhs_alias = query.join(lhs_alias, lhs_column, related_model._table, 'id', lhs_column)
                    sql_field = related_model._field_to_sql(rhs_alias, related_model._rec_name, query)

                if rule.match_mode == 'accent':
                    # Since unaccent is case sensitive, we must add a lower to make sql_field insensitive
                    sql_field = unaccent(SQL('lower(%s)', sql_field))

                sql_group_by = SQL()
                company_field = res_model._fields.get('company_id')
                if company_field and not dm_model.mix_by_company:
                    sql_group_by = SQL(', %s', res_model._field_to_sql(table, 'company_id', query))

                # Get all the rows matching the rule defined
                # (e.g. exact match of the name) having at least 2 records
                # Each row contains the matched value and an array of matching records:
                #   | value matched | {array of record IDs matching the field}
                sql = SQL(
                    """
                    SELECT %(field)s AS group_field_name,
                        array_agg(%(table_id)s ORDER BY %(table_id)s ASC)
                    FROM %(tables)s
                    WHERE length(%(field)s) > 0 AND %(where_clause)s
                    GROUP BY group_field_name %(group_by)s
                    HAVING COUNT(%(field)s) > 1
                    """,
                    field=sql_field,
                    table_id=SQL.identifier(table, 'id'),
                    tables=query.from_clause,
                    where_clause=query.where_clause or SQL("TRUE"),
                    group_by=sql_group_by,
                )

                try:
                    self._cr.execute(sql)
                except ProgrammingError as e:
                    if e.pgcode == errorcodes.UNDEFINED_FUNCTION:
                        raise UserError(_('Missing required PostgreSQL extension: unaccent'))
                    raise

                rows = self._cr.fetchall()
                ids = ids + [row[1] for row in rows]

            # Fetches the IDs of all the records who already matched (and are not merged),
            # as well as the discarded ones.
            # This prevents creating twice the same groups.
            self._cr.execute("""
                SELECT
                    ARRAY_AGG(res_id ORDER BY res_id ASC)
                FROM data_merge_record
                WHERE model_id = %s
                GROUP BY group_id""", [dm_model.id])
            done_groups_res_ids = [set(x[0]) for x in self._cr.fetchall()]

            _logger.info('Query identification done after %s' % str(timeit.default_timer() - t1))
            t1 = timeit.default_timer()
            if ast.literal_eval(self.env['ir.config_parameter'].get_param('data_merge.merge_lists', 'True')):
                merge_list = merge_common_lists
            else:
                merge_list = lambda x: x
            groups_to_create = [set(r) for r in merge_list(ids) if len(r) > 1]
            _logger.info('Merging lists done after %s' % str(timeit.default_timer() - t1))
            t1 = timeit.default_timer()
            _logger.info('Record creation started at %s', str(t1))
            groups_created = 0
            groups_to_create_count = len(groups_to_create)
            for group_to_create in groups_to_create:
                groups_created += 1
                if groups_created % 100 == 0:
                    _logger.info('Created groups %s / %s' % (groups_created, groups_to_create_count))

                # Check if the IDs of the group to create is already part of an existing group
                # e.g.
                #   The group with records A B C already exists:
                #       1/ If group_to_create equals A B, do not create a new group
                #       2/ If group_to_create equals A D, create the new group (A D is not a subset of A B C)
                if any(group_to_create <= x for x in done_groups_res_ids):
                    continue

                group = self.env['data_merge.group'].with_context(prefetch_fields=False).create({'model_id': dm_model.id})
                d = [{'group_id': group.id, 'res_id': rec} for rec in group_to_create]
                self.env['data_merge.record'].with_context(prefetch_fields=False).create(d)

                if groups_created % 1000 == 0 and batch_commits:
                    self.env.cr.commit()

                group._elect_master_record()

                if dm_model.create_threshold > 0 and group.similarity * 100 <= dm_model.create_threshold:
                    group.unlink()
                    continue

                if dm_model.merge_mode == 'automatic':
                    if group.similarity * 100 >= dm_model.merge_threshold:
                        group.merge_records()
                        group.unlink()

            _logger.info('Record creation done after %s' % str(timeit.default_timer() - t1))

    ##############
    ### Overrides
    ##############
    @api.constrains('res_model_id')
    def _check_prevent_merge(self):
        models = set(self.env['ir.model'].browse(self.res_model_id.ids).mapped('model'))
        for model_name in models:
            if model_name and hasattr(self.env[model_name], '_prevent_merge') and self.env[model_name]._prevent_merge:
                raise ValidationError(_('Deduplication is forbidden on the model: %s', model_name))

    def copy(self, default=None):
        self.ensure_one()
        default = default or {}
        if not default.get('name'):
            default['name'] = _('%s (copy)', self.name)
        return super().copy(default)

    def write(self, vals):
        if 'active' in vals and not vals['active']:
            self.env['data_merge.group'].search([('model_id', 'in', self.ids)]).unlink()

        if 'create_threshold' in vals and vals['create_threshold']:
            self.env['data_merge.group'].search([('model_id', 'in', self.ids), ('similarity', '<=', vals['create_threshold'] / 100)]).unlink()

        return super(DataMergeModel, self).write(vals)

    #############
    ### Actions
    #############
    def open_records(self):
        self.ensure_one()

        action = self.env["ir.actions.actions"]._for_xml_id("data_merge.action_data_merge_record")
        action['context'] = dict(ast.literal_eval(action.get('context')), searchpanel_default_model_id=self.id)
        return action

    def action_find_duplicates(self):
        self.sudo().find_duplicates()
        return self.open_records()
