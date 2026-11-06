-- neutralization of Microsoft calendar
UPDATE res_users
    SET microsoft_calendar_token = NULL,
        microsoft_calendar_rtoken = NULL
    WHERE microsoft_calendar_token IS NOT NULL
    OR microsoft_calendar_rtoken IS NOT NULL;


UPDATE microsoft_calendar_credentials
    SET calendar_sync_token = NULL,
        synchronization_stopped = True,
        last_sync_date = NULL
    WHERE calendar_sync_token IS NOT NULL
        OR last_sync_date IS NOT NULL
        OR synchronization_stopped IS NOT TRUE;
