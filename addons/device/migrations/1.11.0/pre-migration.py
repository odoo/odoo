# The MQTT transport left this module for remote_mqtt. Nothing about an
# existing database changes: it had MQTT before, so it gets remote_mqtt now,
# and every record the transport owns is handed over before remote reloads.
#
# The handover has to happen here rather than in remote_mqtt's own hook. Odoo
# drops the ir_model_data rows a module stops declaring, and by the time
# remote_mqtt installs, remote has already been reloaded without them -- so the
# columns, the selection values and the cron would be gone and the devices
# would have lost their protocol.

FIELDS = {
    "remote_config": (
        "mqtt_qos",
        "mqtt_use_tls",
        "mqtt_session_expiry_interval",
        "mqtt_receive_maximum",
        "mqtt_max_packet_size",
        "mqtt_subscribe_topics",
        "mqtt_publish_topic",
    ),
    "remote_device": (
        "mqtt_client_id",
        "mqtt_subscribe_topics",
        "mqtt_publish_topic",
    ),
}

SELECTIONS = (
    "selection__remote_config__protocol__mqtt",
    "selection__remote_device__comm_protocol__mqtt",
    "selection__remote_device_category__comm_protocol__mqtt",
)

# ir.cron delegates to ir.actions.server, and the loader gives the delegate an
# xmlid of its own. Handing over the cron without it leaves the action behind,
# owned by a module that no longer declares it.
CRONS = (
    "ir_cron_mqtt_health_check",
    "ir_cron_mqtt_health_check_ir_actions_server",
)

DEMO = (
    "demo_config_mqtt_standard",
    "demo_config_mqtt_auth",
    "demo_device_temp_sensor_01",
    "demo_device_temp_humidity_01",
    "demo_device_smart_switch_01",
    "demo_device_gps_tracker_01",
    "demo_data_temp_01",
    "demo_data_temp_02",
    "demo_data_temp_03",
    "demo_data_climate_01",
    "demo_data_climate_02",
    "demo_data_switch_01",
    "demo_data_switch_02",
    "demo_data_gps_01",
    "demo_data_gps_02",
)


def migrate(cr, version):
    _install_remote_mqtt(cr)
    _hand_over_data_rows(cr)


def _install_remote_mqtt(cr):
    # Every database that had this module had MQTT in it, so the split must not
    # decide for anyone that they no longer want it. A greenfield install is
    # where the choice is made.
    cr.execute(
        """
        UPDATE ir_module_module
           SET state = 'to install'
         WHERE name = 'remote_mqtt'
           AND state = 'uninstalled'
        """
    )


def _hand_over_data_rows(cr):
    names = [
        *(
            f"field_{model}__{field}"
            for model, fields in FIELDS.items()
            for field in fields
        ),
        *SELECTIONS,
        *CRONS,
        *DEMO,
    ]
    cr.execute(
        """
        UPDATE ir_model_data
           SET module = 'remote_mqtt'
         WHERE module = 'remote'
           AND name = ANY(%s)
           AND NOT EXISTS (
               SELECT 1 FROM ir_model_data existing
                WHERE existing.module = 'remote_mqtt'
                  AND existing.name = ir_model_data.name
           )
        """,
        (names,),
    )
