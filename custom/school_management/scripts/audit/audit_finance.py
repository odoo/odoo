import os
import sys

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import odoo
from odoo.modules.registry import Registry

def test():
    odoo.tools.config.parse_config(['-c', 'odoo.conf', '-d', 'odoo'])
    registry = Registry('odoo')
    with registry.cursor() as cr:
        env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
        Student = env['university.student']
        Fee = env['university.fee']
        Payment = env['university.payment']
        
        overdue_students = Student.search([('financial_status', '=', 'overdue')])
        pending_students = Student.search([('financial_status', '=', 'pending')])
        paid_students = Student.search([('financial_status', '=', 'good_standing')])
        
        print('=== FINANCIAL INTEGRATION AUDIT ===')
        print(f'Total Students: {Student.search_count([])}')
        print(f'Students Overdue: {len(overdue_students)}')
        print(f'Students Pending: {len(pending_students)}')
        print(f'Students Good Standing: {len(paid_students)}')
        print(f'Total Invoices: {Fee.search_count([])}')
        print(f'Invoices Overdue: {Fee.search_count([("payment_state", "=", "overdue")])}')
        print(f'Invoices Partial: {Fee.search_count([("payment_state", "=", "partial")])}')
        print(f'Invoices Paid: {Fee.search_count([("payment_state", "=", "paid")])}')
        print(f'Total Payments: {Payment.search_count([])}')
        
        if overdue_students:
            s = overdue_students[0]
            print(f'\nSample Overdue Student: {s.name} ({s.student_id})')
            print(f'  Balance Due: ${s.fee_balance:.2f}')
            print(f'  Total Fee: ${s.fee_total:.2f} | Paid: ${s.fee_paid:.2f}')
            print(f'  Overdue Count: {s.overdue_fee_count}')
            print(f'  Status: {s.financial_status}')
            unpaid_fee = s.fee_ids.filtered(lambda f: f.payment_state in ('overdue', 'not_paid', 'partial'))[:1]
            if unpaid_fee:
                print(f'  Unpaid Fee Invoice: {unpaid_fee.name} - ${unpaid_fee.balance:.2f} (Due: {unpaid_fee.due_date}, Payment State: {unpaid_fee.payment_state})')
                print(f'  Reminders Sent: {unpaid_fee.reminder_count}')
                print(f'  Last Reminder Date: {unpaid_fee.last_reminder_date}')

if __name__ == '__main__':
    test()
