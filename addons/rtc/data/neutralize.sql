-- * delete SFU keys
DELETE FROM ir_config_parameter
    WHERE key IN ('rtc.sfu_server_key');
