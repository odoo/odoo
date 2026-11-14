import psycopg2

conn = psycopg2.connect(dbname='odoo', user='odoo', password='rithdev22', host='127.0.0.1', port=5432)
cur = conn.cursor()
cur.execute("SELECT id, name, report_name, report_type, print_report_name FROM ir_act_report_xml WHERE model = 'university.payment'")
print('Payment reports:', cur.fetchall())
cur.execute("SELECT id, name, report_name, report_type, print_report_name FROM ir_act_report_xml WHERE model = 'university.report.card'")
print('Report card:', cur.fetchall())
conn.close()
