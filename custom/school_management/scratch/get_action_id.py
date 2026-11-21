import psycopg2

conn = psycopg2.connect('dbname=odoo user=odoo password=rithdev22 host=127.0.0.1 port=5432')
cur = conn.cursor()
cur.execute("SELECT res_id, name, model FROM ir_model_data WHERE module='school_management' AND (name LIKE '%student%' OR name LIKE '%action%')")
for row in cur.fetchall():
    print(row)
