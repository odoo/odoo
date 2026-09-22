import logging

_logger = logging.getLogger(__name__)

OBSOLETE_INDEXES = [
    "device_data_log__value_numeric_index",
    "device_data_log__metric_name_index",
    "device_data_log__quality_index",
    "device_data_log__data_type_index",
    "device_data_log__source_index",
    "device_data_log__timestamp_index",
    "device_data_log_gps__latitude_index",
    "device_data_log_gps__longitude_index",
    "device_data_log_gps__odometer_valid_index",
    "device_data_log_gps__ignition_anomaly_index",
    "device_data_log_gps__data_type_index",
    "device_data_log_gps__source_index",
    "device_data_log_gps__timestamp_index",
]

OBSOLETE_PARAMETERS = [
    "device.polling_interval",
    "device.health_check_interval",
    "device.auto_reconnect_enabled",
]


def migrate(cr, version):
    if not version:
        return

    for index_name in OBSOLETE_INDEXES:
        cr.execute(f'DROP INDEX IF EXISTS "{index_name}"')
    _logger.info(
        "19.0.1.3.0: dropped %s obsolete single-column index(es) on the "
        "time-series tables.",
        len(OBSOLETE_INDEXES),
    )

    cr.execute(
        """
        UPDATE device_kind
        SET disconnect_timeout_seconds = 3600
        WHERE code = 'gps_tracker' AND COALESCE(disconnect_timeout_seconds, 0) = 0
        """
    )
    if cr.rowcount:
        _logger.info(
            "19.0.1.3.0: set the GPS tracker category staleness timeout to 3600s."
        )

    cr.execute(
        "DELETE FROM ir_config_parameter WHERE key = ANY(%s)",
        (OBSOLETE_PARAMETERS,),
    )
    if cr.rowcount:
        _logger.info(
            "19.0.1.3.0: removed %s write-only configuration parameter(s); the "
            "Settings page now edits the scheduled actions directly.",
            cr.rowcount,
        )
