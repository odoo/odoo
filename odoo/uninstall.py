# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import psycopg2

from itertools import groupby
from functools import reduce
from odoo.exceptions import MissingError
from odoo.tools import intercept_logger
from odoo.tools import PrimalGraph, RecordCollector, RelationalGraph

_logger = logging.getLogger(__name__)

ORM_TABLES = [
    'ir.model', 'ir.model.fields', 'ir.model.fields.selection',
    'ir.model.relation', 'ir.model.constraint',
]


class Uninstaller:
    def __init__(self, data, constraints, relations, level=2):
        self.env = data.env
        self.pool = data.pool
        self.graphs = [
            PrimalGraph(constructor=lambda x: x) for index in range(0, level)
        ]
        self.node_lookup = {}
        self.model_nodes = {}
        self.extra_steps = {}

        # Do not delete records that have other external ids (and thus do not
        # belong to the modules being installed).
        self.env.cr.execute('''
            SELECT included_data.id
            FROM ir_model_data AS included_data
            LEFT JOIN ir_model_data AS excluded_data
            ON included_data.res_id = excluded_data.res_id
            AND included_data.model = excluded_data.model
            AND excluded_data.id NOT IN %s
            WHERE included_data.id IN %s
            AND excluded_data.id IS NULL
            ORDER BY included_data.model, included_data.res_id
        ''', (data._ids or (None,), data._ids or (None,)))
        data = data.browse(rec[0] for rec in self.env.cr.fetchall())

        self.data_by_model = {
            model: self.env[model].browse(ref.res_id for ref in refs)
            for model, refs in groupby(data, lambda ref: ref.model)
        }

        self.data_lookup = {
            self.env[ref.model].browse(ref.res_id): ref.name for ref in data
        }

        Model = self.env['ir.model']
        Field = self.env['ir.model.fields']
        Constraint = self.env['ir.model.constraint']
        Relation = self.env['ir.model.relation']

        self.models = self.data_by_model.get('ir.model', Model)
        self.fields = self.data_by_model.get('ir.model.fields', Field)

        self.simple_fields = self.fields.filtered(lambda field: (
            field.ttype not in ('one2many', 'many2one', 'many2many')
            and not field.related_field_id and not field.related,
        ))

        # Add missing relation tables. For example, the relation table for an
        # inherited many2many field defined in another module will not be
        # marked for removal.
        relations |= Relation.search([
            ('name', 'in', self.fields.mapped('relation_table')),
            ('name', 'not in', Field.search([
                ('id', 'not in', self.fields.ids),
                ('relation_table', 'in', self.fields.mapped('relation_table')),
                ('relation_table', '!=', False),
            ]).mapped('relation_table')),
        ])

        if constraints:
            self.data_by_model.setdefault('ir.model.constraint', Constraint)
            self.data_by_model['ir.model.constraint'] |= constraints

        if relations:
            self.data_by_model.setdefault('ir.model.relation', Relation)
            self.data_by_model['ir.model.relation'] |= relations

        for records in self.data_by_model.values():
            self.build_node(records)

        # Cache all display names so that we don't have to perform read
        # operations anymore while removing data. For example, when failing to
        # remove a record that no longer exists (perhaps it was previously
        # cascade deleted), this can pose problems.
        self.display_names = {model: {
            record.id: (
                record.display_name
                if model != 'ir.model.fields'
                else f'{record.name} for {record.model}'
            ) for record in records
        } for model, records in self.data_by_model.items()}

        # Cache all field model names.
        self.model_names = {field: field.model for field in self.fields}
        self.build_graph()

    def build_node(self, node):
        self.extra_steps.setdefault(node, [])
        for graph in self.graphs:
            graph.build_nodes(node)

    def build_step(self, node, step):
        assert not node or node._name in self.data_by_model
        assert not node or not (node - self.data_by_model[node._name])
        self.build_node(node)
        self.extra_steps[node].append(step)

    def build_edge(self, source, target, optionality=0):
        '''
        @param {BaseModel} dependency: a recordset
        @param {BaseModel} dependent: another recordset that should be removed
        after the first one
        @param {int} [optionality=0]: A higher optionality means the dependency
        is less required. Zero optionality means the dependency cannot be
        skipped.
        '''
        assert not source or source._name in self.data_by_model
        assert not target or target._name in self.data_by_model
        assert not source or not (source - self.data_by_model[source._name])
        assert not target or not (target - self.data_by_model[target._name])
        self.build_node(source)
        self.build_node(target)
        for index in range(0, len(self.graphs) - optionality):
            self.graphs[index].build_edges(target, source)

    def uninstall(self, component=None, level=0):
        # Initialize a recordset to collect xml ids that cannot be deleted.
        undeletable = self.env['ir.model.data']

        if component is None:
            component = self.graphs[level]
        else:
            component = component & self.graphs[level]

        for component in component.components():
            if len(component) == 1:
                records = list(component.graph_nodes)[0]
                if len(records) == 1:
                    name = self.display_names[records._name][records.id]
                    _logger.info('Deleting %s named %s', records, name)
                elif records._name == 'ir.model.fields' and len(records) > 1:
                    models = list(set(records.mapped(lambda field: (
                        self.model_names[field]
                    ))))
                    _logger.info('Deleting %s for models %s', records, models)
                else:
                    _logger.info('Deleting %s', records)
                undeletable |= self.delete(records.exists(), silent=True)
            elif level + 1 < len(self.graphs):
                _logger.info('\n'.join(['Removing cycles from component'] + [
                    f'    Node {node} depends on\n' + '\n'.join([
                        f'        Node {dependency}' for dependency in dependencies
                    ]) for node, dependencies in component.graph_nodes.items()
                ]))
                undeletable |= self.uninstall(component, level + 1)
            else:
                _logger.error('\n'.join(['Cycles detected in uninstall graph'] + [
                    f'    Node {node} depends on\n' + '\n'.join([
                        f'        Node {dependency}' for dependency in dependencies
                    ]) for node, dependencies in component.graph_nodes.items()
                ]))
                raise RuntimeError('Cycles detected in uninstall graph')

        # Sort out which undeletable model data may have become deletable again
        # because of records being cascade deleted or tables being dropped.
        remaining = self.env['ir.model.data']
        for data in undeletable.exists():
            record = self.env[data.model].browse(data.res_id)
            try:
                with self.env.cr.savepoint():
                    if record.exists():
                        # Record exists, therefore the data is still
                        # undeletable, add it to remaining records.
                        remaining |= data
                        name = self.display_names[record._name][record.id]
                        _logger.warning('Undeletable record %s named %s', *[
                            record, name,
                        ])
                        continue
            except psycopg2.ProgrammingError:
                # This most likely means that the record does not exist, since
                # record.exists() is rougly equivalent to `SELECT id FROM table
                # WHERE id=record.id` and it may raise a ProgrammingError
                # because the table no longer exists (and so does the record),
                # also applies to ir.model.fields, constraints, etc.
                pass
        # remove remaining module data records
        (undeletable.exists() - remaining).unlink()
        return remaining

    def delete(self, records, silent=False):
        '''
        This method tries to unlink a recordset.

        :param records: The recordset targeted for removal
        :param silent: Will supress exceptions if true
        :return: A recordset with any remaining undeletable records
        '''
        undeletable = self.env['ir.model.data']

        stack = [records]
        while len(stack) > 0:
            records = stack.pop()
            if len(records) == 0:
                continue
            try:
                log_level = None
                if len(records) == 1:
                    log_level = logging.WARNING
                with self.env.cr.savepoint(), intercept_logger('odoo.sql_db', max_log_level=log_level):
                    for group in self.graphs[0].groups(records):
                        for execute_step in self.extra_steps[group]:
                            execute_step()
                    if records._name == 'ir.model.relation':
                        records._module_data_uninstall()
                    elif records._name == 'ir.model.constraint':
                        records._module_data_uninstall()
                    else:
                        records.unlink()
            except Exception as error:
                if len(records) > 1:
                    # divide the batch in two, and recursively delete them
                    half_size = len(records) // 2
                    stack.append(records[:half_size])
                    stack.append(records[half_size:])
                    continue

                log_function = _logger.warning
                if isinstance(error, MissingError):
                    # TODO Perhaps check if the missing record corresponds to
                    # the one we are trying to delete.
                    log_function = _logger.info

                name = self.display_names[records._name][records.id]
                log_function('Unable to delete %s named %s', *[
                    records, name,
                ], exc_info=True)
                undeletable |= undeletable.search([
                    ('model', '=', records._name),
                    ('res_id', 'in', records.ids),
                ])

        if not silent and len(undeletable) > 0:
            raise RuntimeError(f'Unable to remove {undeletable}')

        return undeletable

    def build_graph(self):
        '''
        Build a dependency graph defining the removal order of the data being
        uninstalled. A node in the graph is identified by a recordset.
        '''

        orm_tables = [
            'ir.model', 'ir.model.fields', 'ir.model.fields.selection',
            'ir.model.relation', 'ir.model.constraint',
        ]

        # Records in orm tables are not generally represented as a single node
        # in the graph, which means we cannot simply define dependencies for
        # all targeted records in an orm table. This can be circumvented by
        # defining dummy nodes using empty recordsets having all nodes in the
        # same orm table as its dependents.
        Model = self.env['ir.model']
        Field = self.env['ir.model.fields']
        Value = self.env['ir.model.fields.selection']
        Constraint = self.env['ir.model.constraint']
        Relation = self.env['ir.model.relation']

        selections = self.data_by_model.get('ir.model.fields.selection', Value)
        constraints = self.data_by_model.get('ir.model.constraint', Constraint)
        relations = self.data_by_model.get('ir.model.relation', Relation)

        groups = self.data_by_model.get('res.groups', self.env['res.groups'])

        models_by_name = {model.model: model for model in self.models}

        # Sometimes translation between a field object in the registry and the
        # equivalent in the database is needed.
        field_lookup = {
            self.env[field.model]._fields[field.name]: field
            for field in self.fields
        }

        # In general, the dependency graph for records associated to a certain
        # model will look like this:
        #
        # +------------+      +-------------+      +-----------+
        # | Data       | ---> | Constraints | ---> | Relations |
        # +------------+      +-------------+      +-----------+
        #       |                    |                   |
        #       v                    v                   v
        # +------------+      +-------------+      +-----------+
        # | Selections | ---> | Fields      | ---> | Model     |
        # +------------+      +-------------+      +-----------+
        #
        # From the dependencies in this graph the following will be generated
        # by the relational fields dependency discovery:
        #
        # * Selection values -> Field
        # * Fields           -> Model
        # * Constraints      -> Model
        # * Relations        -> Model
        #
        # The other dependencies have to be manually added to the graph.

        #######################################################################
        # Generate selection value removal nodes                              #
        #######################################################################

        # Selection values should be removed before any fields. Depending on
        # its ondelete value, removing a selection value potentially calls
        # unlink.

        selections_by_model = reduce(lambda result, v: result.update({
            v.field_id.model: result.get(v.field_id.model, Value) + v
        }) or result, selections, {})

        #######################################################################
        # Generate removal nodes for model data                               #
        #######################################################################

        for model, records in self.data_by_model.items():
            self.build_node(self.env[model])

            if model not in orm_tables:
                self.build_edge(self.env[model], records)
                self.build_edge(records, self.fields)

                if model in selections_by_model:
                    self.build_edge(records, selections_by_model[model])

        #######################################################################
        # Generate model removal nodes                                        #
        #######################################################################

        for model in models_by_name:
            self.build_edge(Model, models_by_name[model])

        #######################################################################
        # Generate many2many relation removal nodes                           #
        #######################################################################

        self.build_edge(Relation, relations)

        # for model, model_relations in relations_by_model.items():
        #     self.build_edge(Relation, model_relations)

        #     if model in models_by_name:
        #         self.build_edge(model_relations, models_by_name[model])

        #######################################################################
        # Generate field removal nodes                                        #
        #######################################################################

        relation_map = {relation.name: relation for relation in relations}
        fields_by_model = {
            model: self.fields.filtered(lambda field: field.model == model)
            for model in set(self.fields.mapped('model'))
        }

        self.build_edge(Field, self.fields)
        for model, fields in fields_by_model.items():
            if model in self.data_by_model and model not in orm_tables:
                self.build_edge(self.data_by_model[model], fields)

            if model in models_by_name:
                self.build_edge(fields, models_by_name[model])

            # if model in selections_by_model:
            #     self.build_edge(selections_by_model[model], fields)

        for field in self.fields:
            # avoid prefetching fields that are going to be deleted: during
            # uninstall, it is possible to perform a recompute (via flush_env)
            # after the database columns have been deleted but before the new
            # registry has been created, meaning the recompute will be executed
            # on a stale registry, and if some of the data for executing the
            # compute methods is not in cache it will be fetched, and fields
            # that exist in the registry but not in the database will be
            # prefetched, this will of course fail and prevent the uninstall.
            if self.env[field.model]._fields[field.name] is not None:
                self.env[field.model]._fields[field.name].prefetch = False

        for field in self.fields - self.simple_fields:
            # One2many fields depend on their inverses
            dependent = field.relation_field_id
            if not dependent and field.relation_field:
                dependent = field._get(field.relation, field.relation_field)

            # Related fields depend on their associated fields
            dependent = field.related_field_id
            if not dependent and field.related:
                dependent = field._related_field()

            if dependent and dependent in self.fields:
                self.build_edge(field, dependent)

            # Relational fields are a dependency for their comodels.
            if field.relation in models_by_name:
                assert field.ttype in ('many2one', 'one2many', 'many2many')
                self.build_edge(field, models_by_name[field.relation])

            # Relation tables can be removed after their associated fields.
            if field.relation_table in relation_map:
                assert field.ttype == 'many2many'
                dependent = relation_map[field.relation_table]
                self.build_edge(field, dependent)

            if field.model in models_by_name:
                self.build_edge(field, field.model_id)

        #######################################################################
        # Generate contraint removal nodes                                    #
        #######################################################################

        relations_by_model = reduce(lambda result, r: result.update({
            r.model.model: result.get(r.model.model, Relation) + r
        }) or result, relations, {})

        constraints_by_model = reduce(lambda result, c: result.update({
            c.model.model: result.get(c.model.model, Constraint) + c
        }) or result, constraints, {})

        for model, model_constraints in constraints_by_model.items():
            self.build_edge(Constraint, model_constraints)

            if model in models_by_name:
                self.build_edge(model_constraints, models_by_name[model])

            if model in self.data_by_model and model not in orm_tables:
                self.build_edge(self.data_by_model[model], model_constraints)

            if model in relations_by_model:
                # Generally relation tables are removed at the very end (after
                # the models). However, for models that are kept, the following
                # dependency ensures constraints are removed first.
                self.build_edge(model_constraints, relations_by_model[model])

        #######################################################################
        # Generate foreign key based dependencies between model data          #
        #######################################################################

        # In general, data referencing data from other models will be removed
        # before the data they are referencing. This means every many2one field
        # involving a model and comodel that both have data being targeted for
        # removal will generate a dependency.

        for model, records in self.data_by_model.items():
            is_orm_table = model in orm_tables

            # TODO What should happen for orm models? Specifically for fields
            # and those that depend on fields.
            if records not in self.graphs[0]:
                _logger.info('Many2one dependencies on %s skipped', model)
                continue

            # When unlinking data, manual access rights checks may potentially
            # depend on user groups that will also be removed.
            if not is_orm_table and model != 'res.groups' and len(groups) > 0:
                self.build_edge(records, groups)

        #######################################################################
        # Recover transitive dependencies induced by relational fields        #
        #######################################################################

        # The set_null_step method returns a callable that accepts a recordset
        # and will set a given many2one field on the recordset to null whenever
        # the id is contained in a list of given ids.
        def set_null_step(records, corecords, field):
            def execute_step():
                if not field_lookup.get(field, Field).exists():
                    return

                self.env.cr.execute(f'''
                    UPDATE "{records._table}" SET "{field.name}" = NULL
                    FROM "{records._table}" AS old_values
                    WHERE "{records._table}".id = old_values.id
                    AND "{records._table}".id IN ({','.join(map(str, records.ids))})
                    AND "{records._table}"."{field.name}" IN ({','.join(map(str, corecords.ids))})
                    RETURNING old_values.id, old_values."{field.name}"
                ''')
                results = self.env.cr.dictfetchall()
                updated = records.browse(row['id'] for row in results)
                detached = corecords.browse(row[field.name] for row in results)
                if len(updated) > 0:
                    _logger.info('Decoupled %s from %s', updated, detached)

            return execute_step

        # The goal is to identify any two pairs of models where deleting the
        # records of the first model might potentially cause a foreign key
        # violation on the second model. Such pairs exist for all combinations
        # of models related by a restricted foreign key, either on the model
        # itself or on the many-to-many table relating the two. However these
        # are not the only such pairs that exist. For any pair of the type
        # described above, additional pairs might exist between models whenever
        # these models have cascading foreign key chains linking them to the
        # corresponding models in the base pair.

        # The problem essentially boils down to finding concatenated paths from
        # traversals on three different graphs:
        # 1) We will call the first graph the forward graph. It includes edges
        #    induced by cascade deleted one2many fields.
        # 2) The second part is generated by traversals on the restrict graph:
        #    the graph including edges induced by restricted one2many fields.
        # 3) Finally, the reverse graph is induced by many2one cascade deleted
        #    fields.
        # Concatenated paths from these three graphs will induce a dependency
        # on our removal graph if both the following conditions apply:
        # 1) The starting node of the path is a recordset included in the
        #    original data marked for removal.
        # 2) The path includes at least one edge from the restrict graph.
        forward_graph = RelationalGraph(self.pool, reverse=True)
        forward_graph.include(lambda field: (
            field.type == 'many2one' and field.store
            and not field.company_dependent and field.ondelete == 'cascade'
        ))

        # FIXME Expand restrict fields with set null fields that are part of a
        # constraint (these are potentially restricted FK's in disguise). These
        # fields
        restrict_graph = RelationalGraph(self.pool, reverse=True)
        restrict_graph.include(lambda field: (
            field.type in ('many2one', 'many2many') and field.store
            and not field.company_dependent and field.ondelete == 'restrict'
        ))

        reverse_graph = RelationalGraph(self.pool)
        reverse_graph.include(lambda field: (
            field.type == 'many2one' and field.store
            and not field.company_dependent and field.ondelete == 'cascade'
        ))

        collector = RecordCollector()

        for records in self.data_by_model.values():
            collector.add(records)

        nodes = self.data_by_model.values()

        for node in collector:
            prefixes = forward_graph.shortest_paths(node, RecordCollector)
            for prefix in prefixes:
                records = prefix.nodes[0]
                sources = [prefix.nodes[-1]]
                centers = restrict_graph.shortest_paths(sources, RecordCollector)

                for center in centers:
                    target = center.nodes[-1]
                    corecords = target.filtered(lambda record: record in collector)
                    is_nullable = center.edges and not center.edges[0].required
                    if is_nullable:
                        edge = center.edges[0]
                        step = set_null_step(center.nodes[1], center.nodes[0], edge)
                    if prefix.edges + center.edges and corecords:
                        if is_nullable:
                            self.build_step(records, step)
                        self.build_edge(corecords, records, optionality=1)

                    # We require the chain to contain minimum one restricted field.
                    if not center.edges:
                        continue

                    suffixes = reverse_graph.shortest_paths([
                        target.filtered(lambda record: record not in collector)
                    ], RecordCollector)

                    for suffix in suffixes:
                        head_count = len(prefix.edges + center.edges)
                        tail_count = len(suffix.edges)
                        nodes = prefix.nodes[:-1] + center.nodes[:-1] + suffix.nodes

                        if not suffix.edges:
                            # Trivial suffixes were already taken care of.
                            continue

                        if not nodes[-1]:
                            continue

                        # for i in reversed(range(head_count, head_count + tail_count)):
                        #     model = self.env[edges[i].model_name]
                        #     nodes[i] &= model.search([
                        #         (edges[i].name, 'in', nodes[i + 1].ids),
                        #     ])

                        # for i in reversed(range(0, head_count)):
                        #     nodes[i] &= nodes[i + 1][edges[i].name]

                        # if head_count + tail_count > 1:
                        #     print(f'Source {[self.data_lookup[record] for record in nodes[0]]}')
                        #     print(f'Target {[self.data_lookup[record] for record in nodes[-1]]}')
                        #     print(f'Fields {edges}')
                        #     print(f'Chain  {nodes}')

                        # FIXME Dependency == dependent??
                        target = nodes[-1]
                        corecords = target.filtered(lambda record: record in collector)
                        if corecords._name == records._name:
                            records -= corecords
                        if not corecords or not records:
                            continue
                        if head_count + tail_count > 0 and corecords:
                            if is_nullable:
                                self.build_step(records, step)
                            self.build_edge(corecords, records, optionality=int(bool(is_nullable)))
