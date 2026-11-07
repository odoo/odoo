-- neutralization of Microsoft calendar
UPDATE res_users
    SET microsoft_calendar_token = NULL,
        microsoft_calendar_rtoken = NULL
    WHERE microsoft_calendar_token IS NOT NULL
       OR microsoft_calendar_rtoken IS NOT NULL;

UPDATE res_users_settings
    SET microsoft_calendar_sync_token = NULL,
        microsoft_last_sync_date = NULL;
