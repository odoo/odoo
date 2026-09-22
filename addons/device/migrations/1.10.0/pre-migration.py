def migrate(cr, version):
    # remote.http_timeout_default, remote.ws_ping_interval_default and
    # remote.data_retention_days_default were seeded on every install and read
    # by nothing. The HTTP path reads config_id.http_timeout with a literal
    # fallback, the websocket key belongs to remote_websocket, and the settings
    # wizard binds the near-miss key remote.data_retention_days. The records are
    # noupdate="1", so dropping them from the data file does not remove them
    # from a database that already has them.
    keys = [
        "remote.http_timeout_default",
        "remote.ws_ping_interval_default",
        "remote.data_retention_days_default",
    ]
    cr.execute("DELETE FROM ir_config_parameter WHERE key = ANY(%s)", (keys,))
    cr.execute(
        """
        DELETE FROM ir_model_data
         WHERE module = 'remote'
           AND model = 'ir.config_parameter'
           AND name = ANY(%s)
        """,
        (
            [
                "param_http_timeout_default",
                "param_ws_ping_interval_default",
                "param_data_retention_days_default",
            ],
        ),
    )
    _drop_numeric_metric_columns(cr)


def _drop_numeric_metric_columns(cr):
    # value_numeric, value_boolean and metric_name had no writer: the only
    # producer, _store_data_point, has always written data_type json plus
    # value_json, and the two readers that filtered on data_type = numeric
    # (get_time_series, prepare_statistics) had no caller outside the tests.
    cr.execute(
        """
        SELECT 1 FROM information_schema.columns
         WHERE table_name = 'remote_data_log' AND column_name = 'value_numeric'
        """
    )
    if not cr.fetchone():
        return
    cr.execute(
        """
        ALTER TABLE remote_data_log
            DROP COLUMN value_numeric,
            DROP COLUMN value_boolean,
            DROP COLUMN metric_name
        """
    )
    cr.execute(
        """
        DELETE FROM ir_model_fields
         WHERE model = 'remote.data.log'
           AND name = ANY(%s)
        """,
        (["value_numeric", "value_boolean", "metric_name"],),
    )
