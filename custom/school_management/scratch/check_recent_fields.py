import psycopg2

conn = psycopg2.connect(dbname='odoo', user='odoo', password='rithdev22', host='127.0.0.1', port=5432)
cur = conn.cursor()
cur.execute("SELECT id, name, model, field_description, ttype, state, create_date FROM ir_model_fields ORDER BY id DESC LIMIT 30;")
for row in cur.fetchall():
    print(row)
