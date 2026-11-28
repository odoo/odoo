import psycopg2
conn = psycopg2.connect(dbname='odoo', user='odoo', password='rithdev22', host='127.0.0.1', port=5432)
cur = conn.cursor()
cur.execute("""
    SELECT rc.id, rc.name, ay.name as year, sem.name as sem, rc.gpa, rc.total_credits
    FROM university_report_card rc
    JOIN university_academic_year ay ON ay.id = rc.academic_year_id
    JOIN university_semester sem ON sem.id = rc.semester_id
    WHERE rc.id IN (105, 106)
""")
print(cur.fetchall())
conn.close()
