-- disable website_event_jitsi
DELETE FROM ir_config_parameter
WHERE key = 'website_event_jitsi.jitsi_server_domain';
