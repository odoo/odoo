def migrate(cr, version):
    cr.execute("""
        UPDATE hr_leave
        SET request_unit_custom = FALSE
        WHERE request_unit_custom = TRUE
        AND (holiday_status_id IS NOT NULL OR request_unit_half OR request_unit_hours);
    """)
