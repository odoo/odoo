from odoo import models, fields


class PgIndexes(models.Model):
    _name = 'pg.indexes'
    _description = "PosgreSQL Indexes"
    _auto = False

    tablename = fields.Char(help="Name of table the index is for")
    indexname = fields.Char(help="Name of index")
    indexdef = fields.Text(help="Index definition (a reconstructed CREATE INDEX command)")
    indexsize = fields.Integer()
    idx_scan = fields.Integer(help="Number of index scans initiated on this index")
    idx_tup_read = fields.Integer(help="Number of index entries returned by scans on this index")
    idx_tup_fetch = fields.Integer(help="Number of live table rows fetched by simple index scans using this index")

    @property
    def _table_query(self):
        return """
            SELECT tablename || ',' || indexname AS id,
                   tablename,
                   indexname,
                   indexdef,
                   pg_table_size(pg_stat_user_indexes.indexrelid) AS indexsize,
                   idx_scan,
                   idx_tup_read,
                   idx_tup_fetch
              FROM pg_indexes
              JOIN pg_stat_user_indexes ON pg_indexes.tablename = pg_stat_user_indexes.relname
                                       AND pg_indexes.indexname = pg_stat_user_indexes.indexrelname
             WHERE pg_indexes.schemaname = 'public'
        """

    def drop_index(self):
        self.env.cr.execute(f"""DROP INDEX "{self.indexname}";""")  # pylint: disable=sql-injection
