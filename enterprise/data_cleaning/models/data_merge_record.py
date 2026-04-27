# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast
import itertools
import logging
from collections.abc import Iterable
from datetime import datetime, date

import psycopg2
import psycopg2.errors

from odoo import api, fields, models
from odoo.exceptions import ValidationError, UserError
from odoo.models import MAGIC_COLUMNS
from odoo.osv.expression import FALSE_DOMAIN, OR, expression
from odoo.tools import _, get_lang, SQL
from odoo.tools.misc import format_datetime, format_date, partition as tools_partition, unique

_logger = logging.getLogger(__name__)
ALLOWED_COMPANY_OPERATORS = ['not in', 'in', '=', '!=', 'ilike', 'not ilike', 'like', 'not like']


class DataMergeRecord(models.Model):
    _name = 'data_merge.record'
    _description = 'Deduplication Record'
    _order = 'res_id desc'

    active = fields.Boolean(compute='_compute_active', store=True)
    group_id = fields.Many2one('data_merge.group', string='Record Group', ondelete='cascade', required=True, index=True)
    model_id = fields.Many2one(related='group_id.model_id', store=True, readonly=True, index=True)
    res_model_id = fields.Many2one(related='group_id.res_model_id', store=True, readonly=True, index=True)
    res_model_name = fields.Char(related='group_id.res_model_name', store=True, readonly=True)
    is_master = fields.Boolean(default=False)
    is_deleted = fields.Boolean(compute='_compute_fields')
    is_discarded = fields.Boolean(default=False)

    # Original Record
    name = fields.Char(compute='_compute_fields')
    res_id = fields.Integer(string='Record ID', readonly=False, aggregator=None, index=True)
    record_create_date = fields.Datetime(string='Created On', compute='_compute_fields')
    record_create_uid = fields.Char(string='Created By', compute='_compute_fields')
    record_write_date = fields.Datetime(string='Updated On', compute='_compute_fields')
    record_write_uid = fields.Char(string='Updated By', compute='_compute_fields')
    company_id = fields.Many2one('res.company', compute='_compute_fields', search='_search_company_id')

    differences = fields.Char(string='Differences',
        help='Differences with the master record', compute='_compute_differences', store=True)
    field_values = fields.Char(string='Field Values',
        compute='_compute_field_values')
    used_in = fields.Char(string='Used In',
        help='List of other models referencing this record', compute='_compute_usage', store=True)

    #############
    ### Searchs
    #############

    def _search_company_id(self, operator, value):
        """ Build a subquery to be used in the domain returned by this search method.

            There can be two types of res_model_names regarding the company_id field.
            Either the corresponding env[res_model_name] records have a company_id field or they don't.
            In the first case we add a where condition for each distinct res_model_name.
            In the second case we either return all the records or no records, depending
            on the (operator, value) pair.
        """
        if operator not in ALLOWED_COMPANY_OPERATORS:
            raise NotImplementedError()

        cr = self._cr
        # flush in case record was just created but not yet in database
        self.env['data_merge.model'].flush_model()
        restrict_model_ids = self.env.context.get('data_merge_model_ids')
        if restrict_model_ids:
            cr.execute(
                """
                SELECT m.res_model_name,
                       m.res_model_id
                  FROM data_merge_model m
                 WHERE m.id IN %s
                """,
                [restrict_model_ids],
            )
        else:
            # SELECT DISTINCT res_model_name FROM data_merge_record
            # is 7 times slower for 5 millions of data.merge.record
            cr.execute(
                """
                SELECT m.res_model_name,
                       m.res_model_id
                  FROM data_merge_model m
                 WHERE m.id IN (SELECT r.model_id FROM data_merge_record r)
                """
            )
        # Remove duplicated value and preserve order
        models_info = list(unique(r for r in cr.fetchall() if r[0] in self.env))
        if not models_info:
            # Initial select id query to apply ir.rules and build Query object.
            query = self.env['data_merge.record'].with_context(active_test=False)._search([])
            # no models => return all records
            return [('id', 'in', query)]

        models_with_company, models_no_company = tools_partition(
            lambda r: self.env[r[0]]._fields.get('company_id'),
            models_info,
        )

        # Whether a domain leaf (False, operator, value) should be considered as True
        false_company_domain_is_true = (
            (operator in ('not ilike', 'not like')) or
            (operator in ('=', 'ilike', 'like') and not value) or
            (operator == '!=' and value) or
            (
                isinstance(value, Iterable) and
                (
                    (operator == 'in' and False in value) or
                    (operator == 'not in' and False not in value)
                )
            )
        )

        # Build a query to filter by company_id
        join_queries = []
        where_queries = []
        if models_no_company and false_company_domain_is_true:
            where_queries.append(SQL(
                "res_model_id IN %s",
                tuple(r[1] for r in models_no_company),
            ))
        for model_name, model_id in models_with_company:
            Model = self.env[model_name]
            # Adapt operator and value for direct SQL query
            exp = expression([('company_id', operator, value)], Model)
            self._apply_ir_rules(exp.query)
            from_clause, where_clause = exp.query.from_clause, exp.query.where_clause
            model_table = Model._table
            from_sql_code = from_clause.code
            assert from_sql_code.startswith(f'"{model_table}"') and not from_clause.params
            extra_joins = SQL(from_sql_code[len(f'"{model_table}"'):])

            join_queries.append(SQL(
                """
                LEFT JOIN %s
                ON data_merge_record.res_id = %s.id
                %s
                """,
                SQL.identifier(model_table),
                SQL.identifier(model_table),
                extra_joins,
            ))
            where_queries.append(SQL(
                "(%s AND data_merge_record.res_model_id = %s)",
                where_clause, model_id,
            ))
        if not where_queries:
            # there was a nonempty models_info but no subqueries
            # it means that nothing satisfies the domain
            return FALSE_DOMAIN
        sql = SQL(
            """(
            SELECT data_merge_record.id
            FROM data_merge_record
            %s
            WHERE %s
            )""",
            SQL(" ").join(join_queries),
            SQL(" OR ").join(where_queries),
        )
        return [('id', 'in', sql)]


    #############
    ### Computes
    #############
    def _render_values(self, to_read):
        self.ensure_one()

        def format_value(value, env):
            if isinstance(value, tuple):
                return value[1]
            if isinstance(value, datetime):
                return format_datetime(env, value, dt_format='short')
            if isinstance(value, date):
                return format_date(env, value)
            return value

        IrField = lambda key: self.env['ir.model.fields']._get(self.res_model_name, key)
        field_description = lambda key: IrField(key)['field_description']

        # Hide fields with an attr 'groups' defined or from the blacklisted fields
        model_fields = self.env[self.res_model_name]._fields
        hidden_field = lambda key: key in MAGIC_COLUMNS or \
            key not in model_fields or \
            model_fields[key].groups or \
            not model_fields[key].export_string_translation or \
            IrField(key)['ttype'] == 'binary'

        record = self._original_records()
        if not record:
            return dict()

        record_data = record.read(to_read)[0]
        return {str(field_description(key)):format_value(value, self.env) for key, value in record_data.items() if value and not hidden_field(key)}

    @api.depends('res_id')
    def _compute_field_values(self):
        model_fields = {}
        for record in self:
            if record.model_id not in model_fields.keys():
                model_fields[record.model_id] = record.model_id.rule_ids.mapped('field_id.name')
            to_read = model_fields[record.model_id]

            if not to_read:
                record.field_values = ''
            else:
                record.field_values = ', '.join([v for k,v in record._render_values(to_read).items()])

    @api.depends('res_id')
    def _compute_differences(self):
        for record in self:
            if record.group_id.divergent_fields:
                read_fields = record.group_id.divergent_fields.split(',')
                record.differences = ', '.join(['%s: %s' % (k, v) for k,v in record._render_values(read_fields).items()])
            else:
                record.differences = ''

    def _get_references(self):
        """
        Count all the references for the records.

        :return dict of tuples with the record ID as key
            (count, model, model name, fields)
                - `count`: number of records
                - `model`: technical model name (res.partner)
                - `model name`: "human" name (Contact)
                - `fields`: list of fields from the model referencing the record
        """
        res_models = list(set(self.mapped('res_model_name')))
        # Get the relevant fields for each model
        model_fields = dict.fromkeys(res_models, self.env['ir.model.fields'])
        all_fields = self.env['ir.model.fields'].sudo().search([
            ('store', '=', True),
            ('ttype', 'in', ('one2many', 'many2one', 'many2many')),
            ('relation', 'in', res_models),
            ('index', '=', True),
        ])
        for field in all_fields:
            if not isinstance(self.env[field.model], models.BaseModel) or \
                    not self.env[field.model]._auto or \
                    self.env[field.model]._transient:
                continue
            model_fields[field.relation] |= field

        # Map the models with their business names
        model_name = {field.model: field.model_id.name for field in all_fields}

        # Compute the references per record
        references = {record.id: [] for record in self}
        # Should be only one on the business flow, but who knows
        for res_model_name in res_models:
            records = self.filtered(lambda r: r.res_model_name == res_model_name)
            records_mapped = {record.res_id: record.id for record in records}
            reference_fields = model_fields[res_model_name]

            # Group the fields per model
            group_model_fields = {field.model: [] for field in reference_fields}
            for field in reference_fields:
                group_model_fields[field.model].append(field.name)


            for model in group_model_fields:
                ref_fields = group_model_fields[model]  # fields for the model
                domain = OR([[(f, 'in', records.mapped('res_id'))] for f in ref_fields])
                groupby_field = ref_fields[0]
                count_grouped = self.env[model]._read_group([(groupby_field, '!=', False)] + domain, [groupby_field], ['__count'])
                for group_value, count in count_grouped:
                    record_id = records_mapped.get(group_value.id)
                    if not record_id:
                        continue
                    references[record_id].append((count, model_name[model]))
        return references

    @api.depends('res_id')
    def _compute_usage(self):
        if ast.literal_eval(self.env['ir.config_parameter'].sudo().get_param('data_merge.compute_references', 'True')):
            references = self._get_references()
            for record in self:
                ref = references[record.id]
                record.used_in = ', '.join(['%s %s' % (r[0], r[1]) for r in ref])
        else:
            self.used_in = ''

    @api.depends('res_model_name', 'res_id')
    def _compute_fields(self):
        groups = itertools.groupby(self, key=lambda r: r.res_model_name)
        for _, group_records in groups:
            group_records_ids = [r.id for r in group_records]
            records = self.browse(group_records_ids)
            existing_records = {r.id:r for r in records._original_records()}

            for record in records:
                original_record = existing_records.get(record.res_id) or self.env[record.res_model_name]
                name = original_record.display_name
                record.is_deleted = record.res_id not in existing_records.keys()
                record.name = name if name else '*Record Deleted*'
                record.company_id = original_record._fields.get('company_id') and original_record.company_id
                record.record_create_date = original_record.create_date
                record.record_create_uid = original_record.create_uid.name or '*Deleted*'
                record.record_write_date = original_record.write_date
                record.record_write_uid = original_record.write_uid.name or '*Deleted*'


    @api.depends('is_deleted', 'is_discarded')
    def _compute_active(self):
        for record in self:
            record.active = not (record.is_deleted or record.is_discarded)

    def _original_records(self):
        if not self:
            return []

        model_name = set(self.mapped('res_model_name')) or {}

        if len(model_name) != 1:
            raise ValidationError(_('Records must be of the same model'))

        model = model_name.pop()
        ids = self.mapped('res_id')
        return self.env[model].with_context(active_test=False).sudo().browse(ids).exists()

    def _record_snapshot(self):
        """ Snapshot of the original record, to be logged in the chatter when merged """
        self.ensure_one()
        return self._render_values([])

    ############
    ### Helpers
    ############
    @api.model
    def _get_model_references(self, table):
        """
        Get all the foreign key referring to `table`.

        e.g. _get_model_references('res_company') -> {'res_partner': ['company_id']}

        :param str table: name of the table
        :returns a dict with table name as keys and the list of fields referenced as values
        :rtype: dict
        """
        query = """
            SELECT cl1.relname as table, array_agg(att1.attname) as columns
            FROM pg_constraint as con, pg_class as cl1, pg_class as cl2, pg_attribute as att1, pg_attribute as att2
            WHERE con.conrelid = cl1.oid
                AND con.confrelid = cl2.oid
                AND array_lower(con.conkey, 1) = 1
                AND con.conkey[1] = att1.attnum
                AND att1.attrelid = cl1.oid
                AND att2.attname = 'id'
                AND array_lower(con.confkey, 1) = 1
                AND con.confkey[1] = att2.attnum
                AND att2.attrelid = cl2.oid
                AND con.contype = 'f'
                AND cl2.relname = %s
            GROUP BY cl1.relname"""

        self.env.flush_all()
        self._cr.execute(query, (table, ))
        return {r[0]:r[1] for r in self._cr.fetchall()}

    @api.model
    def _update_foreign_keys(self, destination, source):
        """
        Update all the foreign keys referring to `source` records with `destination` as new referencee.
        The parameters are the real records and not data_merge.record

        :param destination: destination record of the foreign keys
        :param source: list of records
        """
        references = self._get_model_references(destination._table)

        source_ids = source.ids
        self.env.flush_all()

        for table, columns in references.items():
            for column in columns:
                query_dict = {
                    'table': table,
                    'column': column,
                }

                # Query to check the number of columns in the referencing table
                query = SQL(
                    """
                    SELECT COUNT("column_name")
                    FROM "information_schema"."columns"
                    WHERE "table_name" ILIKE %s
                    """, query_dict['table']
                )
                [[column_count]] = self.env.execute_query(query)

                ## Relation table for M2M
                if column_count == 2:
                    # Retrieve the "other" column
                    query = SQL(
                        """
                        SELECT "column_name"
                        FROM "information_schema"."columns"
                        WHERE
                            "table_name" LIKE %s
                        AND "column_name" <> %s
                        """,
                        query_dict['table'],
                        query_dict['column'],
                    )
                    [[othercol]] = self.env.execute_query(query)
                    query_dict.update({'othercol': othercol})

                    for rec_id in source_ids:
                        # This query will filter out existing records
                        # e.g. if the record to merge has tags A, B, C and the master record has tags C, D, E
                        #      we only need to add tags A, B
                        query = SQL(
                            """
                            UPDATE %(table)s o
                            SET %(column)s =  %(destination_id)s  --- master record
                            WHERE %(column)s = %(record_id)s      --- record to merge
                            AND NOT EXISTS (
                                SELECT 1
                                FROM  %(table)s i
                                WHERE %(column)s = %(destination_id)s
                                AND i.%(othercol)s = o.%(othercol)s
                            )
                            """,
                            table=SQL.identifier(query_dict['table']),
                            column=SQL.identifier(query_dict['column']),
                            othercol=SQL.identifier(query_dict['othercol']),
                            destination_id=destination.id,
                            record_id=rec_id,
                        )
                        self.env.execute_query(query)
                else:
                    sql_table = SQL.identifier(query_dict['table'])
                    sql_column = SQL.identifier(query_dict['column'])
                    for rec_id in source_ids:
                        try:
                            with self._cr.savepoint():
                                self.env.execute_query(SQL(
                                    """
                                    UPDATE %(table)s o
                                    SET %(column)s  = %(destination_id)s  --- master record
                                    WHERE %(column)s = %(record_id)s      --- record to merge
                                    """,
                                    table=sql_table,
                                    column=sql_column,
                                    destination_id=destination.id,
                                    record_id=rec_id,
                                ))
                        except psycopg2.errors.UniqueViolation:
                            _logger.warning('Query %s failed, due to an unique constraint', query)
                        except psycopg2.IntegrityError as e:
                            _logger.warning('Query %s failed', query)
                        except psycopg2.Error:
                            raise ValidationError(_('Query Failed.'))

        self._merge_additional_models(destination, source_ids)
        fields_to_recompute = [f.name for f in destination._fields.values() if f.compute and f.store]
        destination.modified(fields_to_recompute)
        self.env.flush_all()
        self.env.invalidate_all()

    ## Manual merge of ir.attachment & mail.activity
    @api.model
    def _merge_additional_models(self, destination, source_ids):
        if hasattr(destination, 'message_follower_ids'):
            self._merge_mail_followers(destination, self.env[destination._name].browse(source_ids))
        models_to_adapt = [
            {
                'table': 'ir_attachment',
                'id_field': 'res_id',
                'model_field': 'res_model',
            }, {
                'table': 'mail_activity',
                'id_field': 'res_id',
                'model_field': 'res_model',
            }, {
                'table': 'ir_model_data',
                'id_field': 'res_id',
                'model_field': 'model',
            }, {
                'table': 'mail_message',
                'id_field': 'res_id',
                'model_field': 'model',
            }
        ]
        query = """
            UPDATE %(table)s
            SET %(id_field)s = %%(destination_id)s
            WHERE %(id_field)s = %%(record_id)s
            AND %(model_field)s = %%(model)s"""
        for model in models_to_adapt:
            q = query % model
            for rec_id in source_ids:
                try:
                    with self._cr.savepoint():
                        params = {
                            'destination_id': destination.id,
                            'record_id': rec_id,
                            'model': destination._name
                        }
                        self._cr.execute(q, params)
                except psycopg2.errors.UniqueViolation:
                    _logger.warning('Query %s failed, due to an unique constraint', query)
                except psycopg2.IntegrityError as e:
                    _logger.warning('Query %s failed', query)
                except psycopg2.Error:
                    raise ValidationError(_('Query Failed.'))

        # Company-dependent fields
        with self._cr.savepoint():
            for fname, field in destination._fields.items():
                if field.company_dependent:
                    self._cr.execute(SQL(
                        # TODO check if orderby is needed to get deterministic result
                        """
                        UPDATE %(table)s
                        SET %(col)s = NULLIF(
                            (
                                SELECT jsonb_object_agg(key, value)
                                FROM %(table)s, jsonb_each(%(col)s)
                                WHERE id IN %(source_ids)s
                            ) || COALESCE(%(col)s, '{}'::jsonb),
                            '{}'::jsonb
                        )
                        WHERE id = %(destination_id)s
                        """,
                        table=SQL.identifier(destination._table),
                        col=SQL.identifier(fname),
                        destination_id=destination.id,
                        source_ids=tuple(source_ids),
                    ))

    def _merge_mail_followers(self, destination, source):
        """ Using the default merge method risks duplicating the SQL key for mail_followers (res_model, res_id, partner_id).
        Adding a partner as follower to a record twice nullifies the transaction, preventing the merge of followers.
        This function ensures we don't try unsafe subscriptions.
        """
        dest_followers = destination.message_follower_ids.partner_id
        new_followers = source.message_follower_ids.partner_id - dest_followers
        destination.message_subscribe(new_followers.ids)

    #############
    ### Override
    #############
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            group = self.env['data_merge.group'].browse(vals['group_id'])
            if 'res_id' not in vals:
                raise ValidationError(_('There is not referenced record'))
            record = self.env[group.res_model_name].browse(vals['res_id'])

            if not record.exists():
                raise ValidationError(_('The referenced record does not exist'))
        return super().create(vals_list)


    def write(self, vals):
        if 'is_master' in vals and vals['is_master']:
            master = self.with_context(active_test=False).group_id.record_ids.filtered('is_master')
            master.write({'is_master': False})

        return super(DataMergeRecord, self).write(vals)

    ############
    ### Actions
    ############
    def open_record(self):
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': self.res_model_name,
            'res_id': self.res_id,
            'context': {
                'create': False,
                'edit': False
            }
        }

    def action_deduplicates(self, records):
        """ This action is called when hitting the contextual merge action
        and redirects the user to the 'Deduplication' view of the data_merge
        module, using the selected contextual data.
        In order to be able to merge the selected records via the existing
        deduplication flow, all the necessary data_merge.record,
        data_merge.group and data_merge.model are created (or reused if
        already existing).

        :param records: contextual active (or selected) records.
        :return: ir.actions.act_window that redirects to the deduplicate view.
        """
        MergeRecord = self.env['data_merge.record']
        MergeModel = self.env['data_merge.model']
        MergeGroup = self.env['data_merge.group']

        active_ids = records.ids
        active_model = records._name

        if len(active_ids) < 2:
            translated_desc = records.with_context(lang=get_lang(self.env).code)._description
            raise UserError(_("You must select at least two %s in order to merge them.", translated_desc))
        if active_model not in self.env:
            raise ValidationError(_('The target model does not exists.'))

        # prepare action to return
        view = self.env.ref('data_cleaning.data_merge_record_view_search_merge_action')
        action = {
            'name': _('Deduplicate'),
            'view_mode': 'list',
            'res_model': 'data_merge.record',
            'type': 'ir.actions.act_window',
            'search_view_id': [view.id, 'search'],
            'domain': [('res_id', 'in', active_ids), ('res_model_name', '=', active_model)],
            'context': {'group_by': ['group_id']},
            'help': '<p class="o_view_nocontent_smiling_face">%s</p>' % _('No duplicates found')
        }

        # ensure merge action specific record is created in data_merge.model
        merge_model = MergeModel.with_context(active_test=False).search([
            ('res_model_name', '=', active_model),
            ('is_contextual_merge_action', '=', True)
        ])
        if not merge_model:
            model_name = self.env['ir.model']._get(active_model).with_context(lang=self.env.user.lang).display_name
            merge_model = MergeModel.create({
                'name': _("Manual Selection - %s", model_name),
                'res_model_id': self.env['ir.model']._get(active_model).id,
                'active': False,
                'is_contextual_merge_action': True,
            })

        # creates a new group to put every selected records inside it.
        merge_group = MergeGroup.create({'model_id': merge_model.id})

        # get records from data_merge.records model related to active records
        results = MergeRecord.search_read([
            ('res_id', 'in', active_ids),
            ('res_model_name', '=', active_model)
        ], fields=['res_id'])
        existing_records = {result['res_id']: result['id'] for result in results}

        records_to_create = []
        records_to_update = []
        for record in records:
            if record.id not in existing_records.keys():
                records_to_create.append({
                    'res_id': record.id,
                    'model_id': merge_model.id,
                    'group_id': merge_group.id
                })
            else:
                records_to_update.append(existing_records[record.id])

        MergeRecord.browse(records_to_update).write({
            'group_id': merge_group.id,
            'is_master': False
        })
        MergeRecord.create(records_to_create)

        return action
