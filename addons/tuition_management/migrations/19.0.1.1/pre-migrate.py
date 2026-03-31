import os
import shutil


def migrate(cr, version):
    """Add name column to profile tables if it doesn't exist, populating from first/last name."""

    # Clear __pycache__ to ensure fresh Python files are loaded
    module_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    for root, dirs, files in os.walk(module_path):
        for d in dirs:
            if d == '__pycache__':
                shutil.rmtree(os.path.join(root, d), ignore_errors=True)

    # Student Profile
    cr.execute("SELECT column_name FROM information_schema.columns WHERE table_name='student_profile' AND column_name='name'")
    if not cr.fetchone():
        cr.execute("ALTER TABLE student_profile ADD COLUMN name VARCHAR")
        cr.execute("""
            UPDATE student_profile 
            SET name = COALESCE(first_name, '') || 
                       CASE WHEN middle_name IS NOT NULL AND middle_name != '' THEN ' ' || middle_name ELSE '' END || 
                       ' ' || COALESCE(last_name, '')
        """)
        cr.execute("UPDATE student_profile SET name = TRIM(name)")
        cr.execute("UPDATE student_profile SET name = 'Unknown' WHERE name IS NULL OR name = ''")

    # Tutor Profile
    cr.execute("SELECT column_name FROM information_schema.columns WHERE table_name='tutor_profile' AND column_name='name'")
    if not cr.fetchone():
        cr.execute("ALTER TABLE tutor_profile ADD COLUMN name VARCHAR")
        cr.execute("""
            UPDATE tutor_profile 
            SET name = COALESCE(first_name, '') || 
                       CASE WHEN middle_name IS NOT NULL AND middle_name != '' THEN ' ' || middle_name ELSE '' END || 
                       ' ' || COALESCE(last_name, '')
        """)
        cr.execute("UPDATE tutor_profile SET name = TRIM(name)")
        cr.execute("UPDATE tutor_profile SET name = 'Unknown' WHERE name IS NULL OR name = ''")

    # Parent Profile
    cr.execute("SELECT column_name FROM information_schema.columns WHERE table_name='parent_profile' AND column_name='name'")
    if not cr.fetchone():
        cr.execute("ALTER TABLE parent_profile ADD COLUMN name VARCHAR")
        cr.execute("""
            UPDATE parent_profile 
            SET name = COALESCE(first_name, '') || 
                       CASE WHEN middle_name IS NOT NULL AND middle_name != '' THEN ' ' || middle_name ELSE '' END || 
                       ' ' || COALESCE(last_name, '')
        """)
        cr.execute("UPDATE parent_profile SET name = TRIM(name)")
        cr.execute("UPDATE parent_profile SET name = 'Unknown' WHERE name IS NULL OR name = ''")

    # Enquiry - populate name from first/middle/last if name column doesn't exist or is empty
    cr.execute("SELECT column_name FROM information_schema.columns WHERE table_name='enquiry' AND column_name='name'")
    if cr.fetchone():
        cr.execute("""
            UPDATE enquiry 
            SET name = COALESCE(first_name, '') || 
                       CASE WHEN middle_name IS NOT NULL AND middle_name != '' THEN ' ' || middle_name ELSE '' END || 
                       ' ' || COALESCE(last_name, '')
            WHERE name IS NULL OR name = ''
        """)
        cr.execute("UPDATE enquiry SET name = TRIM(name) WHERE name IS NOT NULL")
    else:
        cr.execute("ALTER TABLE enquiry ADD COLUMN name VARCHAR")
        cr.execute("""
            UPDATE enquiry 
            SET name = COALESCE(first_name, '') || 
                       CASE WHEN middle_name IS NOT NULL AND middle_name != '' THEN ' ' || middle_name ELSE '' END || 
                       ' ' || COALESCE(last_name, '')
        """)
        cr.execute("UPDATE enquiry SET name = TRIM(name)")

    # Enquiry - populate student_name from student first/middle/last
    cr.execute("SELECT column_name FROM information_schema.columns WHERE table_name='enquiry' AND column_name='student_name'")
    if cr.fetchone():
        cr.execute("""
            UPDATE enquiry 
            SET student_name = COALESCE(student_first_name, '') || 
                       CASE WHEN student_middle_name IS NOT NULL AND student_middle_name != '' THEN ' ' || student_middle_name ELSE '' END || 
                       ' ' || COALESCE(student_last_name, '')
            WHERE student_name IS NULL OR student_name = ''
        """)
        cr.execute("UPDATE enquiry SET student_name = TRIM(student_name) WHERE student_name IS NOT NULL")
    else:
        cr.execute("ALTER TABLE enquiry ADD COLUMN student_name VARCHAR")
        cr.execute("""
            UPDATE enquiry 
            SET student_name = COALESCE(student_first_name, '') || 
                       CASE WHEN student_middle_name IS NOT NULL AND student_middle_name != '' THEN ' ' || student_middle_name ELSE '' END || 
                       ' ' || COALESCE(student_last_name, '')
        """)
        cr.execute("UPDATE enquiry SET student_name = TRIM(student_name)")