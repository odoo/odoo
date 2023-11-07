from odoo import models, fields


class PgIndexes(models.Model):
    _name = 'pg.stat.activity'
    _description = "PosgreSQL Stat Activity"
    _auto = False

    pid = fields.Integer(help="Process ID of this backend")
    application_name = fields.Char(help="Name of the application that is connected to this backend")
    backend_start = fields.Datetime(help="Time when this process was started. For client backends, this is the time the client connected to the server.")
    xact_start = fields.Datetime(help="Time when this process' current transaction was started, or null if no transaction is active. If the current query is the first of its transaction, this column is equal to the query_start column.")
    query_start = fields.Datetime(help="Time when the currently active query was started, or if state is not active, when the last query was started")
    state_change = fields.Datetime(help="Time when the state was last changed")
    wait_event_type = fields.Char(help="The type of event for which the backend is waiting, if any; otherwise NULL")
    wait_event = fields.Char(help="Wait event name if backend is currently waiting, otherwise NULL")
    state = fields.Selection(
        selection=[
            ('active', 'active'),
            ('idle', 'idle'),
            ('idle in transaction', 'idle in transaction'),
            ('idle in transaction (aborted)', 'idle in transaction (aborted)'),
            ('fastpath function call', 'fastpath function call'),
            ('disabled', 'disabled'),
        ],
        help="""Current overall state of this backend. Possible values are:
            * active: The backend is executing a query.
            * idle: The backend is waiting for a new client command.
            * idle in transaction: The backend is in a transaction, but is not currently executing a query.
            * idle in transaction (aborted): This state is similar to idle in transaction, except one of the statements in the transaction caused an error.
            * fastpath function call: The backend is executing a fast-path function.
            * disabled: This state is reported if track_activities is disabled in this backend.
        """,
    )
    backend_type = fields.Char(help="Type of current backend. Possible types are autovacuum launcher, autovacuum worker, logical replication launcher, logical replication worker, parallel worker, background writer, client backend, checkpointer, archiver, startup, walreceiver, walsender and walwriter. In addition, background workers registered by extensions may have additional types.")

    @property
    def _table_query(self):
        return self.env.cr.mogrify("""
            SELECT pid AS id,
                   pid,
                   application_name,
                   backend_start,
                   xact_start,
                   query_start,
                   state_change,
                   wait_event_type,
                   wait_event,
                   state,
                   backend_type
              FROM pg_stat_activity
             WHERE datname = %s
        """, [self.env.cr.dbname]).decode()

    def kill_process(self):
        self.env.cr.execute("SELECT pg_terminate_backend(%s)", [self.pid])
