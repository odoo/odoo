-- neutralization of Google calendar
UPDATE google_calendar_credentials
    SET calendar_rtoken = NULL,
        calendar_token = NULL,
        synchronization_stopped = True
    WHERE calendar_rtoken IS NOT NULL
    OR calendar_token IS NOT NULL
    OR synchronization_stopped IS NOT TRUE;
