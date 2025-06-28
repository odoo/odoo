-- neutralization of Microsoft calendar
UPDATE res_users
    SET microsoft_calendar_token = NULL,
        microsoft_calendar_rtoken = NULL;

UPDATE microsoft_calendar_credentials
    SET calendar_sync_token = NULL,
        synchronization_stopped = True,
        last_sync_date = NULL;
