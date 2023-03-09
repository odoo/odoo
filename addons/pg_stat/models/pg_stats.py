from odoo import models, fields


class PgStats(models.Model):
    _name = 'pg.stats'
    _description = "PosgreSQL Statistics"
    _auto = False

    tablename = fields.Char(help="Name of table")
    attname = fields.Char(help="Name of column described by this row")
    inherited = fields.Boolean(help="If true, this row includes values from child tables, not just the values in the specified table")
    null_frac = fields.Float(help="Fraction of column entries that are null")
    avg_width = fields.Integer(help="Average width in bytes of column's entries")
    n_distinct = fields.Float(help="If greater than zero, the estimated number of distinct values in the column. If less than zero, the negative of the number of distinct values divided by the number of rows. (The negated form is used when ANALYZE believes that the number of distinct values is likely to increase as the table grows; the positive form is used when the column seems to have a fixed number of possible values.) For example, -1 indicates a unique column in which the number of distinct values is the same as the number of rows.")
    most_common_freqs = fields.Json(help="A list of the most common values in the column. (Null if no values seem to be more common than any others.)")
    correlation = fields.Float(help="Statistical correlation between physical row ordering and logical ordering of the column values. This ranges from -1 to +1. When the value is near -1 or +1, an index scan on the column will be estimated to be cheaper than when it is near zero, due to reduction of random access to the disk. (This column is null if the column data type does not have a < operator.)")

    @property
    def _table_query(self):
        return """
            SELECT tablename || ',' || attname AS id,
                   tablename,
                   attname,
                   inherited,
                   null_frac,
                   avg_width,
                   n_distinct,
                   most_common_freqs,
                   correlation
              FROM pg_stats
             WHERE schemaname = 'public'
        """
