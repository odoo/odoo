# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.     
#
##############################################################################
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
        


