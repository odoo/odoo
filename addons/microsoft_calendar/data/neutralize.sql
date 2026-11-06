-- neutralization of Microsoft calendar
UPDATE res_users
    SET microsoft_calendar_token = NULL,
        microsoft_calendar_rtoken = NULL,
        microsoft_synchronization_stopped = True
    WHERE microsoft_calendar_token IS NOT NULL
    OR microsoft_calendar_rtoken IS NOT NULL
    OR microsoft_synchronization_stopped IS NOT TRUE;
