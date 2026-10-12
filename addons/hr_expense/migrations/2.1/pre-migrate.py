from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    xml_ids = [
        'hr_expense.mt_expense_approved',
        'hr_expense.mt_expense_refused',
        'hr_expense.mt_expense_paid',
        'hr_expense.mt_expense_reset',
        'hr_expense.mt_expense_entry_delete',
        'hr_expense.mt_expense_entry_draft',
    ]

    subtype_ids = []
    for xml_id in xml_ids:
        record = env.ref(xml_id, raise_if_not_found=False)
        if record:
            subtype_ids.append(record.id)

    if subtype_ids:
        cr.execute("""
            UPDATE mail_message_subtype
               SET "default" = false
             WHERE id in %s
        """,
        (tuple(subtype_ids),))
