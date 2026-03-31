import os
import shutil


def migrate(cr, version):
    """Populate enquiry name and student_name from first/middle/last name fields."""

    # Enquiry - populate name from first/middle/last
    cr.execute("SELECT column_name FROM information_schema.columns WHERE table_name='enquiry' AND column_name='first_name'")
    if cr.fetchone():
        cr.execute("""
            UPDATE enquiry 
            SET name = TRIM(
                COALESCE(first_name, '') || 
                CASE WHEN middle_name IS NOT NULL AND middle_name != '' THEN ' ' || middle_name ELSE '' END || 
                ' ' || COALESCE(last_name, '')
            )
            WHERE name IS NULL OR name = ''
        """)

    # Enquiry - populate student_name from student first/middle/last
    cr.execute("SELECT column_name FROM information_schema.columns WHERE table_name='enquiry' AND column_name='student_first_name'")
    if cr.fetchone():
        cr.execute("SELECT column_name FROM information_schema.columns WHERE table_name='enquiry' AND column_name='student_name'")
        if not cr.fetchone():
            cr.execute("ALTER TABLE enquiry ADD COLUMN student_name VARCHAR")
        cr.execute("""
            UPDATE enquiry 
            SET student_name = TRIM(
                COALESCE(student_first_name, '') || 
                CASE WHEN student_middle_name IS NOT NULL AND student_middle_name != '' THEN ' ' || student_middle_name ELSE '' END || 
                ' ' || COALESCE(student_last_name, '')
            )
            WHERE student_name IS NULL OR student_name = ''
        """)