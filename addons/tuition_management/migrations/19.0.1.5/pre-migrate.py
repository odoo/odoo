def migrate(cr, version):
    """Clean up duplicate enquiry stages and remove XML ID references."""
    # Remove duplicate stages, keeping the one with the lowest id for each name
    cr.execute("""
        DELETE FROM enquiry_stage
        WHERE id NOT IN (
            SELECT MIN(id) FROM enquiry_stage GROUP BY name
        )
    """)

    # Remove all ir_model_data entries for enquiry.stage so the data file
    # doesn't try to manage them anymore
    cr.execute("""
        DELETE FROM ir_model_data
        WHERE module = 'tuition_management' AND model = 'enquiry.stage'
    """)