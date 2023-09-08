from odoo import api, SUPERUSER_ID


def _fix_mail_channel_rule(env):
    rule = env.ref('mail.mail_channel_rule', raise_if_not_found=False)
    if rule:
        rule.write(
            {
                'domain_force': "['|', ('is_member', '=', True), \
                '&', \
                    ('channel_type', '=', 'channel'), \
                    '|', \
                    ('group_public_id', '=', False), \
                    ('group_public_id', 'in', [g.id for g in user.groups_id])]"
            }
        )


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    _fix_mail_channel_rule(env)
