__name__ = "Convert the Holidays Per User limits into positive leave request"

def migrate(cr, version):
    cr.execute("""SELECT id, employee_id, holiday_status, max_leaves, notes, create_uid
                    FROM hr_holidays_per_user;""")
    for record in cr.fetchall():
        cr.execute("""INSERT INTO hr_holidays 
            (employee_id, type, allocation_type, name, holiday_status_id, 
            state, number_of_days, notes, manager_id) VALUES
            (%s, 'add', 'company', 'imported holiday_per_user', %s,
            'validated', %s, %s, %s) """, (record[1],record[2],record[3],record[4],record[5]))
        


