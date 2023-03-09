from odoo import models, fields


class PgDatabase(models.Model):
    _name = 'pg.stat.database'
    _description = "PosgreSQL Database Stat"
    _auto = False

    numbackends = fields.Integer(help="Number of backends currently connected to this database, or NULL for shared objects. This is the only column in this view that returns a value reflecting current state; all other columns return the accumulated values since the last reset.")
    xact_commit = fields.Integer(help="Number of transactions in this database that have been committed")
    xact_rollback = fields.Integer(help="Number of transactions in this database that have been rolled back")
    blks_read = fields.Integer(help="Number of disk blocks read in this database")
    blks_hit = fields.Integer(help="Number of times disk blocks were found already in the buffer cache, so that a read was not necessary (this only includes hits in the PostgreSQL buffer cache, not the operating system's file system cache)")
    tup_returned = fields.Integer(help="Number of live rows fetched by sequential scans and index entries returned by index scans in this database")
    tup_fetched = fields.Integer(help="Number of live rows fetched by index scans in this database")
    tup_inserted = fields.Integer(help="Number of rows inserted by queries in this database")
    tup_updated = fields.Integer(help="Number of rows updated by queries in this database")
    tup_deleted = fields.Integer(help="Number of rows deleted by queries in this database")
    conflicts = fields.Integer(help="Number of queries canceled due to conflicts with recovery in this database. (Conflicts occur only on standby servers; see pg_stat_database_conflicts for details.)")
    temp_files = fields.Integer(help="Number of temporary files created by queries in this database. All temporary files are counted, regardless of why the temporary file was created (e.g., sorting or hashing), and regardless of the log_temp_files setting.")
    temp_bytes = fields.Integer(help="Total amount of data written to temporary files by queries in this database. All temporary files are counted, regardless of why the temporary file was created, and regardless of the log_temp_files setting.")
    deadlocks = fields.Integer(help="Number of deadlocks detected in this database")
    checksum_failures = fields.Integer(help="Number of data page checksum failures detected in this database (or on a shared object), or NULL if data checksums are not enabled.")
    checksum_last_failure = fields.Datetime(help="Time at which the last data page checksum failure was detected in this database (or on a shared object), or NULL if data checksums are not enabled.")
    blk_read_time = fields.Float(help="Time spent reading data file blocks by backends in this database, in milliseconds (if track_io_timing is enabled, otherwise zero)")
    blk_write_time = fields.Float(help="Time spent writing data file blocks by backends in this database, in milliseconds (if track_io_timing is enabled, otherwise zero)")
    stats_reset = fields.Datetime(help="Time at which these statistics were last reset")

    @property
    def _table_query(self):
        return self.env.cr.mogrify("""
            SELECT datid AS id,
                   numbackends,
                   xact_commit,
                   xact_rollback,
                   blks_read,
                   blks_hit,
                   tup_returned,
                   tup_fetched,
                   tup_inserted,
                   tup_updated,
                   tup_deleted,
                   conflicts,
                   temp_files,
                   temp_bytes,
                   deadlocks,
                   checksum_failures,
                   checksum_last_failure,
                   blk_read_time,
                   blk_write_time,
                   stats_reset
              FROM pg_stat_database
             WHERE datname = %s
        """, [self.env.cr.dbname]).decode()
