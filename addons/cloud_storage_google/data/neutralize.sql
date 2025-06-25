DELETE
FROM ir_config_parameter
WHERE key = 'cloud_storage_google_bucket_name'
OR key = 'cloud_storage_google_account_info';
