-- neutralization of Google calendar
UPDATE res_users_settings
    SET google_calendar_rtoken = NULL,
        google_calendar_token = NULL,
        google_synchronization_stopped = True
    WHERE google_calendar_rtoken IS NOT NULL
    OR google_calendar_token IS NOT NULL
    OR google_synchronization_stopped IS NOT TRUE;
