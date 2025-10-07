# Copyright 2015-2016 Pedro M. Baeza <pedro.baeza@tecnativa.com>
# Copyright 2017 LasLabs Inc.
# License LGPL-3 - See http://www.gnu.org/licenses/lgpl-3.0.html
from odoo import SUPERUSER_ID, api

__all__ = [
    "post_init_hook",
    "uninstall_hook",
]


def set_security_rule(env, rule_ref):
    """Set the condition for multi-company in the security rule.

    :param: env: Environment
    :param: rule_ref: XML-ID of the security rule to change.
    """
    rule = env.ref(rule_ref)
    if not rule:  # safeguard if it's deleted
        return
    rule.write(
        {
            "active": True,
            "domain_force": ("[('company_ids', 'in', [False] + company_ids)]"),
        }
    )


def post_init_hook(cr, rule_ref, model_name):
    """Set the `domain_force` and default `company_ids` to `company_id`.

    Args:
        cr (Cursor): Database cursor to use for operation.
        rule_ref (string): XML ID of security rule to write the
            `domain_force` from.
        model_name (string): Name of Odoo model object to search for
            existing records.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    set_security_rule(env, rule_ref)
    # Copy company values
    model = env[model_name]
    table_name = model._fields["company_ids"].relation
    column1 = model._fields["company_ids"].column1
    column2 = model._fields["company_ids"].column2
    SQL = """
        INSERT INTO {}
        ({}, {})
        SELECT id, company_id FROM {} WHERE company_id IS NOT NULL
        ON CONFLICT DO NOTHING
    """.format(
        table_name,
        column1,
        column2,
        model._table,
    )
    env.cr.execute(SQL)


def uninstall_hook(cr, rule_ref):
    """Restore product rule to base value.

    Args:
        cr (Cursor): Database cursor to use for operation.
        rule_ref (string): XML ID of security rule to remove the
            `domain_force` from.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    # Change access rule
    rule = env.ref(rule_ref)
    rule.write(
        {
            "active": False,
            "domain_force": (" [('company_id', 'in', [False, user.company_id.id])]"),
        }
    )
