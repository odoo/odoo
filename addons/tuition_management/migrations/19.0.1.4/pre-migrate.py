def migrate(cr, version):
    """Clean up duplicate enquiry stages and register XML IDs."""
    # Remove duplicate stages, keeping the one with the lowest id for each name
    cr.execute("""
        DELETE FROM enquiry_stage
        WHERE id NOT IN (
            SELECT MIN(id) FROM enquiry_stage GROUP BY name
        )
    """)

    # Remove any stale ir_model_data entries for enquiry.stage from this module
    cr.execute("""
        DELETE FROM ir_model_data
        WHERE module = 'tuition_management' AND model = 'enquiry.stage'
    """)

    # Register remaining stages as XML IDs so noupdate="1" is respected
    stage_xml_map = {
        'New': 'stage_new',
        'Demo Scheduled': 'stage_demo_scheduled',
        'Completed': 'stage_completed',
        'Enrolled': 'stage_enrolled',
        'Lost': 'stage_lost',
    }
    for stage_name, xml_id in stage_xml_map.items():
        cr.execute("SELECT id FROM enquiry_stage WHERE name = %s ORDER BY id LIMIT 1", (stage_name,))
        row = cr.fetchone()
        if row:
            cr.execute("""
                INSERT INTO ir_model_data (name, module, model, res_id, noupdate)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (xml_id, 'tuition_management', 'enquiry.stage', row[0], True))