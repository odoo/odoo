import psycopg2

with open("custom/school_management/seed/seed_data.sql", encoding="utf-8") as f:
    sql = f.read()

conn = psycopg2.connect(host="localhost", port=5432, user="odoo", dbname="odoo")
conn.autocommit = True
conn.cursor().execute(sql)
conn.close()
print("Done: Seed data loaded successfully!")
