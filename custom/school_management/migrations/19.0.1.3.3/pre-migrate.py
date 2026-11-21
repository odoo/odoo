"""Ensure class_section_id exists and is populated, and activate enrollment form view."""


def migrate(cr, _version):
    # Activate the enrollment form view
    cr.execute(
        """
        UPDATE ir_ui_view 
           SET active = True 
         WHERE model = 'university.enrollment' 
           AND type = 'form';
        """
    )
    # Ensure class_section_id column exists
    cr.execute(
        """
        SELECT column_name 
          FROM information_schema.columns 
         WHERE table_name = 'university_enrollment' 
           AND column_name = 'class_section_id';
        """
    )
    if not cr.fetchone():
        cr.execute(
            """
            ALTER TABLE university_enrollment 
            ADD COLUMN class_section_id integer REFERENCES university_class_section(id) ON DELETE RESTRICT;
            """
        )
    cr.execute(
        """
        UPDATE university_enrollment 
           SET class_section_id = section_id 
         WHERE class_section_id IS NULL AND section_id IS NOT NULL;
        """
    )
