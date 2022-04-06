# -*- coding: utf-8 -*-

from odoo import fields, models, tools
from odoo.tools import OrderedSet


class MissingIndexes(models.Model):
    _name = "missing.index"
    _description = "shows the indexes that are missing from the foreign key fields"
    _table = "o_missing_indexes_fk"
    _auto = False
    _rec_name = "constraint"
    _order = "size_raw desc"

    banane = fields.Char(string="table name", readonly=True)
    orange = fields.Char(string="column name", readonly=True)
    size = fields.Char(string="table size", readonly=True)
    size_raw = fields.Integer(string="table size bytes", readonly=True)

    constraint = fields.Char(string="foreign key name", readonly=True)
    referenced_table = fields.Char(string="reference table", readonly=True)
    index_create_statement = fields.Char(readonly=True)

    def init(self) -> None:
        tools.drop_view_if_exists(self._cr, self._table)
        self._cr.execute(f"""
CREATE OR REPLACE VIEW {self._table} as
SELECT 
        row_number() OVER() AS id,
        c.conrelid::regclass                                               AS "banane",
    /* list of key column names in order */
       string_agg(a.attname, ',' ORDER BY x.n)                            AS orange, 
       pg_catalog.pg_size_pretty(pg_catalog.pg_relation_size(c.conrelid)) AS size,
       pg_catalog.pg_relation_size(c.conrelid)                            as size_raw,
       c.conname                                                          AS constraint,
       c.confrelid::regclass                                              AS referenced_table,
       'create index "' || c.conname || '_idx_fk_auto" on "' || c.conrelid::regclass || '" using btree ("' ||
       string_agg(a.attname, ',' ORDER BY x.n) || '"); '                  as index_create_statement
FROM pg_catalog.pg_constraint c
         /* enumerated key column numbers per foreign key */
         CROSS JOIN LATERAL unnest(c.conkey) WITH ORDINALITY AS x(attnum, n)
    /* name for each key column */
         JOIN pg_catalog.pg_attribute a ON a.attnum = x.attnum AND a.attrelid = c.conrelid
WHERE NOT EXISTS
    /* is there a matching index for the constraint? */
    (SELECT 1
     FROM pg_catalog.pg_index i
     WHERE i.indrelid = c.conrelid
         /* it must not be a partial index */
       AND i.indpred IS NULL
         /* the first index columns must be the same as the
            key columns, but order doesn't matter */
       AND (i.indkey::smallint[])[0:cardinality(c.conkey) - 1]
         OPERATOR (pg_catalog.@>) c.conkey)
  AND c.contype = 'f'
  --AND pg_catalog.pg_relation_size(c.conrelid) > 1000000
GROUP BY c.conrelid, c.conname, c.confrelid
having string_agg(a.attname, ',' ORDER BY x.n) not in ('create_uid', 'write_uid')
        """)

    def create_index(self):
        """
        actually creates the index.
        We might do this in a CRON immediately executed, because it might take some time to create large indexes
        """
        for index in self:
            index_name = f"{index.constraint}_idx_fk_auto"
            tools.create_index(self.env.cr, index_name, index.banane, [index.orange])
            self.env["missing.index_log"].create(
                {"index_command": index.index_create_statement, "action": "created", "index_name": index_name})

    def create_all_large_indexes(self):
        all_indexes = self.search(domain=[('size', '>', 1000000)], order="size")  # get all the indexes, small first
        all_indexes.create_index()


class IndexStatistics(models.Model):
    _name = "index.statistics"
    _description = "shows the usage statistics of any index in postgresql"
    _table = "o_index_statistics"
    _auto = False
    _order = "index_size_raw desc"
    _rec_name = "index_name"

    table_name = fields.Char(string="Table name", readonly=True)
    index_name = fields.Char(string="Index name", readonly=True)
    idx_scan = fields.Integer(string="Number of scans", readonly=True)
    idx_tup_read = fields.Integer(string="Number of tuple returned", readonly=True)
    idx_tup_fetch = fields.Integer(string="Number of fetches", readonly=True)
    index_definition = fields.Char(string="Index definition", readonly=True)
    index_size = fields.Char(string="Index size on disk", readonly=True)
    index_size_raw = fields.Integer(string="Index size on disk in bytes", readonly=True)
    is_unique = fields.Boolean(string="Is unique", readonly=True)
    is_clustered = fields.Boolean(string="Is clustered", readonly=True)
    is_primary = fields.Boolean(string="Is Primary", readonly=True)

    def init(self) -> None:
        tools.drop_view_if_exists(self._cr, self._table)
        self._cr.execute(f"""
CREATE OR REPLACE VIEW {self._table} as
SELECT
        row_number() OVER() AS id,
        relid                                                    as table_id,
        pi2.indexrelid                                           as index_id,
        relname                                                  as table_name,
        indexrelname                                             as index_name,
        idx_scan,
        idx_tup_read,
        idx_tup_fetch,
        indexdef                                                 as index_definition,
        pg_size_pretty(pg_table_size(stat_all_index.indexrelid)) as index_size,
        pg_table_size(stat_all_index.indexrelid)                 as index_size_raw,
        pi2.indisunique                                          as is_unique,
        pi2.indisclustered                                       as is_clustered,
        pi2.indisprimary                                         as is_primary
FROM pg_catalog.pg_stat_all_indexes stat_all_index
         INNER JOIN pg_catalog.pg_indexes pi ON stat_all_index.indexrelname = pi.indexname
         INNER JOIN pg_catalog.pg_index pi2 ON pi2.indexrelid = stat_all_index.indexrelid
WHERE pi.schemaname <> 'pg_catalog'
        """)

    def remove_index(self):
        for index in self:
            tools.drop_index(self.env.cr, index.index_name, index.table_name)
            self.env["missing.index_log"].create(
                {"index_command": index.index_definition, "action": "removed", "index_name": index.index_name})

    def remove_all_unused_indexes(self):
        all_unused_indexes = self.search(domain=[('idx_scan', '=', 0), ('idx_tup_read', '=', 0), ('idx_tup_fetch', '=', 0), ('is_unique', '=', False), ('is_primary', '=', False), ('is_clustered', '=', False)])

        all_impacted_tables = OrderedSet(all_unused_indexes.mapped('table_name'))

        all_unused_indexes.remove_index()

        for impacted_table in all_impacted_tables:
            # pylint: disable=sql-injection
            # input doesn't come from the user
            self.env.cr.execute(f'analyse {impacted_table};')
