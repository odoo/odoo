def migrate(cr, version):
    """Create enquiry.stage table and populate with default stages before ORM loads."""
    # Check if enquiry_stage table exists
    cr.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'enquiry_stage')")
    if not cr.fetchone()[0]:
        cr.execute("""
            CREATE TABLE enquiry_stage (
                id SERIAL PRIMARY KEY,
                name VARCHAR NOT NULL,
                sequence INTEGER DEFAULT 10,
                fold BOOLEAN DEFAULT FALSE,
                create_uid INTEGER,
                create_date TIMESTAMP DEFAULT NOW(),
                write_uid INTEGER,
                write_date TIMESTAMP DEFAULT NOW()
            )
        """)
        stages = [
            ('stage_new', 'New', 10, False),
            ('stage_demo_scheduled', 'Demo Scheduled', 20, False),
            ('stage_completed', 'Completed', 30, False),
            ('stage_enrolled', 'Enrolled', 40, False),
            ('stage_lost', 'Lost', 50, True),
        ]
        for xml_id, name, sequence, fold in stages:
            cr.execute(
                "INSERT INTO enquiry_stage (name, sequence, fold) VALUES (%s, %s, %s) RETURNING id",
                (name, sequence, fold)
            )
            stage_id = cr.fetchone()[0]
            # Register in ir_model_data so noupdate="1" works
            cr.execute("""
                INSERT INTO ir_model_data (name, module, model, res_id, noupdate)
                VALUES (%s, %s, %s, %s, %s)
            """, (xml_id, 'tuition_management', 'enquiry.stage', stage_id, True))

    # Add stage_id column to enquiry if it doesn't exist
    cr.execute("SELECT column_name FROM information_schema.columns WHERE table_name='enquiry' AND column_name='stage_id'")
    if not cr.fetchone():
        cr.execute("ALTER TABLE enquiry ADD COLUMN stage_id INTEGER REFERENCES enquiry_stage(id)")
        
        # Migrate old status values to stage_id
        cr.execute("SELECT column_name FROM information_schema.columns WHERE table_name='enquiry' AND column_name='status'")
        if cr.fetchone():
            status_mapping = {
                'new': 'New',
                'demo_scheduled': 'Demo Scheduled',
                'completed': 'Completed',
                'enrolled': 'Enrolled',
                'lost': 'Lost',
            }
            for status_val, stage_name in status_mapping.items():
                cr.execute("SELECT id FROM enquiry_stage WHERE name = %s LIMIT 1", (stage_name,))
                row = cr.fetchone()
                if row:
                    cr.execute("UPDATE enquiry SET stage_id = %s WHERE status = %s", (row[0], status_val))
            
            # Set default stage for any remaining NULL
            cr.execute("SELECT id FROM enquiry_stage WHERE name = 'New' LIMIT 1")
            row = cr.fetchone()
            if row:
                cr.execute("UPDATE enquiry SET stage_id = %s WHERE stage_id IS NULL", (row[0],))