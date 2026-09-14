-- neutralization of Microsoft calendar
UPDATE res_users
    SET microsoft_calendar_credential_id = NULL,
        microsoft_calendar_token_validity = NULL
  WHERE microsoft_calendar_credential_id IS NOT NULL;

UPDATE res_users_settings
    SET microsoft_calendar_sync_token = NULL,
        microsoft_synchronization_stopped = True,
        microsoft_last_sync_date = NULL;
