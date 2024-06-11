-- neutralization of Google calendar
UPDATE google_calendar_credentials
    SET calendar_rtoken = NULL,
        calendar_token = NULL,
        synchronization_stopped = True;
