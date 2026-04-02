def migrate(cr, version):
    """Add is_won column and mark Enrolled stage as protected."""
    cr.execute("SELECT column_name FROM information_schema.columns WHERE table_name='enquiry_stage' AND column_name='is_won'")
    if not cr.fetchone():
        cr.execute("ALTER TABLE enquiry_stage ADD COLUMN is_won BOOLEAN DEFAULT FALSE")
    cr.execute("UPDATE enquiry_stage SET is_won = TRUE WHERE name = 'Enrolled'")