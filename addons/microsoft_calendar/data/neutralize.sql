-- neutralization of Microsoft calendar
UPDATE res_users
    SET microsoft_calendar_token = NULL,
        microsoft_calendar_rtoken = NULL;

UPDATE res_users_settings
    SET microsoft_calendar_sync_token = NULL,
        microsoft_synchronization_stopped = True,
        microsoft_last_sync_date = NULL;
