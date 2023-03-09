from odoo import models, fields


class PgTables(models.Model):
    _name = 'pg.stat.tables'
    _description = "PosgreSQL Tables Stat"
    _auto = False

    relid = fields.Integer(help="OID of a table")
    relname = fields.Char(help="Name of the schema that this table is in")
    seq_scan = fields.Integer(help="Number of sequential scans initiated on this table")
    seq_tup_read = fields.Integer(help="Number of live rows fetched by sequential scans")
    idx_scan = fields.Integer(help="Number of index scans initiated on this table")
    idx_tup_fetch = fields.Integer(help="Number of live rows fetched by index scans")
    n_tup_ins = fields.Integer(help="Number of rows inserted")
    n_tup_upd = fields.Integer(help="Number of rows updated (includes HOT updated rows)")
    n_tup_del = fields.Integer(help="Number of rows deleted")
    n_tup_hot_upd = fields.Integer(help="Number of rows HOT updated (i.e., with no separate index update required)")
    n_live_tup = fields.Integer(help="Estimated number of live rows")
    n_dead_tup = fields.Integer(help="Estimated number of dead rows")
    n_mod_since_analyze = fields.Integer(help="Estimated number of rows modified since this table was last analyzed")
    last_vacuum = fields.Datetime(help="Last time at which this table was manually vacuumed (not counting VACUUM FULL)")
    last_autovacuum = fields.Datetime(help="Last time at which this table was vacuumed by the autovacuum daemon")
    last_analyze = fields.Datetime(help="Last time at which this table was manually analyzed")
    last_autoanalyze = fields.Datetime(help="Last time at which this table was analyzed by the autovacuum daemon")
    vacuum_count = fields.Datetime(help="Number of times this table has been manually vacuumed (not counting VACUUM FULL)")
    autovacuum_count = fields.Integer(help="Number of times this table has been vacuumed by the autovacuum daemon")
    analyze_count = fields.Integer(help="Number of times this table has been manually analyzed")
    autoanalyze_count = fields.Integer(help="Number of times this table has been analyzed by the autovacuum daemon")
    pg_table_size = fields.Integer(help="Computes the disk space used by the specified table, excluding indexes (but including its TOAST table if any, free space map, and visibility map).")
    pg_indexes_size = fields.Integer(help="Computes the total disk space used by indexes attached to the specified table.")

    @property
    def _table_query(self):
        return """
            SELECT relid AS id,
                   relid,
                   relname,
                   seq_scan,
                   seq_tup_read,
                   idx_scan,
                   idx_tup_fetch,
                   n_tup_ins,
                   n_tup_upd,
                   n_tup_del,
                   n_tup_hot_upd,
                   n_live_tup,
                   n_dead_tup,
                   n_mod_since_analyze,
                   last_vacuum,
                   last_autovacuum,
                   last_analyze,
                   last_autoanalyze,
                   vacuum_count,
                   autovacuum_count,
                   analyze_count,
                   autoanalyze_count,
                   pg_table_size(relid),
                   pg_indexes_size(relid)
              FROM pg_stat_user_tables
        """
