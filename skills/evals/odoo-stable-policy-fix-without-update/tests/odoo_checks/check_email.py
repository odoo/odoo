# Run by test.sh through `odoo-bin shell` (env is the shell's environment):
# change a tracked field on a test_mail ticket, so its follower partner is
# notified by email, then print what the email body shows on one EVAL_RESULT
# line. The transaction is rolled back, so the check can run several times.
import html
import json
import re

env = env(context=dict(env.context, mail_notify_force_send=False, tracking_disable=False))
result = {"error": None}
try:
    partner = env['res.partner'].create({'name': 'Eval Follower', 'email': 'eval.follower@example.com'})
    old, new = env['mail.test.container'].create([{'name': 'Old Box'}, {'name': 'New Box'}])
    ticket = env['mail.test.ticket'].create({'name': 'Eval ticket', 'container_id': old.id})
    env.flush_all()
    env.cr.precommit.run()
    ticket.message_subscribe(
        partner_ids=partner.ids,
        subtype_ids=env.ref('test_mail.st_mail_test_ticket_container_upd').ids,
    )
    ticket.container_id = new
    env.flush_all()
    env.cr.precommit.run()

    label = ticket._fields['container_id'].get_description(env)['string']
    mails = env['mail.mail'].search([('recipient_ids', 'in', partner.ids)])
    body = '\n'.join(mails.mapped('body_html') or [''])
    # the layout's preheader pads with invisible characters: drop them
    text = re.sub(r'[\u034f\u200b\u200c\u00ad]', '', html.unescape(re.sub(r'<[^>]+>', ' ', body)))
    text = re.sub(r'\s+', ' ', text)
    start = text.find('Old Box')
    result.update({
        'emails': len(mails),
        'label': label,
        'line': text[start:start + 31].strip() if start >= 0 else None,
        # "Old Box -> New Box (Container)", with the arrow once and the label in parentheses
        'separators': bool(re.search(
            rf'Old Box\s*→\s*New Box\s*\(\s*{re.escape(label)}\s*\)', text)),
        'stored_body': ticket.message_ids[:1].body,
    })
except Exception as e:  # noqa: BLE001 - reported to the criterion
    result['error'] = f'{type(e).__name__}: {e}'
finally:
    env.cr.rollback()
print('EVAL_RESULT ' + json.dumps(result))
