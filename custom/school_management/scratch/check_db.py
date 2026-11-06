import psycopg2

conn = psycopg2.connect(dbname='odoo', user='odoo', password='rithdev22', host='127.0.0.1', port=5432)
cur = conn.cursor()
cur.execute("SELECT table_name, column_name FROM information_schema.columns WHERE column_name LIKE '%khmer%';")
print('Columns with khmer:', cur.fetchall())

cur.execute("SELECT id, name, model, field_description FROM ir_model_fields WHERE name LIKE '%khmer%';")
print('ir_model_fields with khmer:', cur.fetchall())

cur.execute("SELECT model, count(*) FROM ir_model_fields WHERE name = 'name_khmer' GROUP BY model;")
print('name_khmer by model:', cur.fetchall())
