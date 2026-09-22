import logging

_logger = logging.getLogger(__name__)

OBSOLETE_COLUMNS = {
    "device_profile": [
        "collect_telemetry",
        "collect_sensors",
        "collect_odometer",
        "collect_fuel_level",
        "fuel_reading_type",
        "collect_fuel_historical_consumption",
        "polling_interval",
    ],
    "device_kind": [
        "polling_interval",
    ],
}

OBSOLETE_PARAMETERS = [
    "device.polling_interval_default",
    "device_gps.min_external_voltage",
    "device_gps.max_external_voltage",
    "device_gps.min_internal_voltage",
    "device_gps.max_internal_voltage",
    "device_gps.min_gsm_signal",
    "device_gps.max_gsm_signal",
    "device_gps.max_speed_change_kmh_per_sec",
    "device_gps.speed_validation_window_seconds",
    "device_gps.min_time_interval_seconds",
    "device_gps.max_acceleration_ms2",
    "device_gps.max_realistic_speed_wheel_kmh",
    "device_gps.enable_warnings",
    "device_gps.strict_mode",
    "device_gps.inactivity_warning_enabled",
    "device_gps.inactivity_warning_hours",
    "device_gps.inactivity_inactive_hours",
]


def migrate(cr, version):
    if not version:
        return

    dropped = 0
    for table, columns in OBSOLETE_COLUMNS.items():
        for column in columns:
            cr.execute(f'ALTER TABLE "{table}" DROP COLUMN IF EXISTS "{column}"')
            dropped += 1
    _logger.info("19.0.1.4.0: dropped %s write-only configuration column(s).", dropped)

    cr.execute(
        "DELETE FROM ir_config_parameter WHERE key = ANY(%s)",
        (OBSOLETE_PARAMETERS,),
    )
    if cr.rowcount:
        _logger.info(
            "19.0.1.4.0: removed %s write-only configuration parameter(s).",
            cr.rowcount,
        )

    _backfill_last_log_pointer(cr)


def _backfill_last_log_pointer(cr):
    cr.execute(
        """
        UPDATE device_device dev
        SET log_last_id = latest.id
        FROM (
            SELECT DISTINCT ON (device_id) device_id, id
            FROM device_data_log
            ORDER BY device_id, timestamp DESC, id DESC
        ) AS latest
        WHERE latest.device_id = dev.id AND dev.log_last_id IS DISTINCT FROM latest.id
        """
    )
    if cr.rowcount:
        _logger.info(
            "19.0.1.4.0: backfilled the last-log pointer on %s device(s).",
            cr.rowcount,
        )
