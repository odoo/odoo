-- Remove Map Box Token as it's only valid per DB url
DELETE FROM ir_config_parameter
 WHERE key = 'web_map.token_map_box';
