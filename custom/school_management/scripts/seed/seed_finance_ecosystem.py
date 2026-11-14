import os
import sys
import datetime
import random

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import odoo
from odoo.modules.registry import Registry
from odoo import api, SUPERUSER_ID, fields

def run():
    odoo.tools.config.parse_config(['-c', 'odoo.conf', '-d', 'odoo'])
    registry = Registry('odoo')
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        print("=== SEEDING COMPREHENSIVE FINANCE & PAYMENT ECOSYSTEM ===")

        today = fields.Date.context_today(env['university.fee'])
        sem1 = env['university.semester'].search([('semester_type', '=', 'semester_1'), ('academic_year_id.name', 'ilike', '2026')], limit=1)
        if not sem1:
            sem1 = env['university.semester'].search([('active', '=', True)], limit=1)
        ay = sem1.academic_year_id if sem1 else env['university.academic.year'].search([], limit=1)

        # 1. Ensure Fee Structures
        programs = env['university.program'].search([('active', '=', True)])
        structures = env['university.fee.structure'].search([])
        print(f"Existing Fee Structures: {len(structures)}")

        struct_templates = [
            ("Undergraduate Computing & IT Tuition", 1850.0, [("Semester Tuition Fee", 1500.0), ("Advanced Computing Lab Fee", 200.0), ("Campus IT & Network Fee", 150.0)]),
            ("Undergraduate Software Engineering Tuition", 1950.0, [("Semester Tuition Fee", 1600.0), ("Software Architecture Lab Fee", 200.0), ("Cloud Platform Access", 150.0)]),
            ("Business & Management Standard Tuition", 1500.0, [("Semester Tuition Fee", 1250.0), ("Case Study & Analytics License", 150.0), ("Executive Seminar Access", 100.0)]),
            ("Clinical Medicine Professional Tuition", 2800.0, [("Clinical Medical Tuition", 2200.0), ("Hospital Ward Practicum Fee", 400.0), ("Diagnostic Lab Equipment", 200.0)]),
            ("Nursing & Healthcare Clinical Tuition", 1800.0, [("Nursing Sciences Tuition", 1400.0), ("Clinical Simulation Lab Fee", 250.0), ("Medical Supplies & Asepsis", 150.0)]),
            ("Electrical Engineering Professional Tuition", 2000.0, [("Engineering Core Tuition", 1600.0), ("Circuits & Power Systems Lab", 250.0), ("Electronics Consumables", 150.0)]),
            ("Master of Business Administration (MBA) Executive Fee", 3200.0, [("Executive MBA Tuition", 2600.0), ("Strategic Leadership Seminar", 400.0), ("Global Case Library", 200.0)]),
        ]

        created_structures = 0
        for sname, total, lines in struct_templates:
            existing = env['university.fee.structure'].search([('name', '=', sname)], limit=1)
            if not existing:
                struct = env['university.fee.structure'].create({
                    'name': sname,
                    'academic_year_id': ay.id if ay else False,
                    'semester_id': sem1.id if sem1 else False,
                    'line_ids': [(0, 0, {'name': lname, 'amount': lamt}) for lname, lamt in lines]
                })
                created_structures += 1
                print(f"  + Created Structure: {sname} (${total:.2f})")

        all_structures = env['university.fee.structure'].search([])

        # 2. Process All Students
        all_students = env['university.student'].search([('status', 'in', ('active', 'suspended'))])
        print(f"\nProcessing {len(all_students)} active students for financial status...")

        created_invoices = 0
        created_payments = 0
        overdue_invoices_count = 0

        for idx, student in enumerate(all_students):
            # Check if student already has a posted invoice for Semester 1
            existing_invoice = student.fee_ids.filtered(lambda f: f.state in ('posted', 'paid'))
            
            if not existing_invoice:
                # Pick fee structure based on program or random
                struct = all_structures[idx % len(all_structures)]
                
                # Determine scenario:
                # idx % 4 == 0: Overdue alert (due date in past)
                # idx % 4 == 1: Fully Paid
                # idx % 4 == 2: Partially Paid
                # idx % 4 == 3: Pending future payment
                scenario = idx % 4

                if scenario == 0:
                    # OVERDUE (e.g. Due 10 days ago)
                    due_date = today - datetime.timedelta(days=random.randint(5, 20))
                elif scenario == 1:
                    # FULLY PAID
                    due_date = today + datetime.timedelta(days=15)
                elif scenario == 2:
                    # PARTIAL
                    due_date = today + datetime.timedelta(days=10)
                else:
                    # PENDING (Due in 14-30 days)
                    due_date = today + datetime.timedelta(days=random.randint(14, 30))

                fee_vals = struct._prepare_fee_vals(student)
                fee_vals.update({
                    'date': today - datetime.timedelta(days=random.randint(15, 30)),
                    'due_date': due_date,
                    'academic_year_id': ay.id if ay else False,
                    'semester_id': sem1.id if sem1 else False,
                })

                fee = env['university.fee'].create(fee_vals)
                fee.action_post()
                created_invoices += 1

                if scenario == 1:
                    # Settle in full with payment
                    pay_method = random.choice(['bank_transfer', 'credit_card', 'cash'])
                    pay_ref = f"TXN-{(idx + 1000):06d}"
                    payment = env['university.payment'].create({
                        'student_id': student.id,
                        'fee_id': fee.id,
                        'amount': fee.total_amount,
                        'date': today - datetime.timedelta(days=random.randint(2, 10)),
                        'payment_method': pay_method,
                        'reference': pay_ref,
                    })
                    payment.action_post()
                    created_payments += 1
                elif scenario == 2:
                    # Settle 50%
                    half_amount = round(fee.total_amount * 0.5, 2)
                    pay_method = random.choice(['bank_transfer', 'cash'])
                    pay_ref = f"DEP-{(idx + 2000):06d}"
                    payment = env['university.payment'].create({
                        'student_id': student.id,
                        'fee_id': fee.id,
                        'amount': half_amount,
                        'date': today - datetime.timedelta(days=random.randint(3, 12)),
                        'payment_method': pay_method,
                        'reference': pay_ref,
                    })
                    payment.action_post()
                    created_payments += 1
                elif scenario == 0:
                    # Send alert notice and log reminder
                    fee.action_send_payment_reminder()
                    overdue_invoices_count += 1
            else:
                # If invoice exists and is posted with balance > 0 and past due date
                for fee in existing_invoice:
                    if not fee.due_date:
                        fee.due_date = today - datetime.timedelta(days=random.randint(5, 15))
                    fee._compute_payment_state()
                    if fee.payment_state == 'overdue' and fee.reminder_count == 0:
                        fee.action_send_payment_reminder()
                        overdue_invoices_count += 1

        # Recompute students financial status
        all_students._compute_fee_totals()
        all_students._compute_financial_status()

        # Summary
        overdue_students = env['university.student'].search([('financial_status', '=', 'overdue')])
        pending_students = env['university.student'].search([('financial_status', '=', 'pending')])
        paid_students = env['university.student'].search([('financial_status', '=', 'good_standing')])

        cr.commit()

        print("\n===========================================================")
        print(">>> FINANCE & PAYMENT SEEDING COMPLETED SUCCESSFULLY <<<")
        print(f"Total Fee Structures: {len(env['university.fee.structure'].search([]))}")
        print(f"New Fee Invoices Created: {created_invoices} (Total Now: {len(env['university.fee'].search([]))})")
        print(f"New Payments Posted: {created_payments} (Total Now: {len(env['university.payment'].search([]))})")
        print(f"Students with Overdue Payment Alert: {len(overdue_students)}")
        print(f"Students with Tuition Pending: {len(pending_students)}")
        print(f"Students with Fees Paid in Good Standing: {len(paid_students)}")
        print("===========================================================")

if __name__ == '__main__':
    run()
