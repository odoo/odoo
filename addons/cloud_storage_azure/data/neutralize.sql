DELETE
FROM ir_config_parameter
WHERE key IN ('cloud_storage_azure_account_name',
              'cloud_storage_azure_container_name',
              'cloud_storage_azure_tenant_id',
              'cloud_storage_azure_client_id',
              'cloud_storage_azure_client_secret')
