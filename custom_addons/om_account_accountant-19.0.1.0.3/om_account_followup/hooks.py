from odoo.exceptions import UserError


ACCOUNTING_STACK_B = [
    "base_account_budget",
    "base_accounting_kit",
    "dynamic_accounts_report",
]


def _ensure_exclusive_modules(env_or_cr, module_name, conflicting_modules, family_label):
    cr = getattr(env_or_cr, "cr", env_or_cr)
    names = sorted({name for name in conflicting_modules if name and name != module_name})
    cr.execute(
        """
        SELECT name, state
        FROM ir_module_module
        WHERE name = ANY(%s)
          AND state IN %s
        ORDER BY name
        """,
        (names, ("installed", "to install", "to upgrade")),
    )
    conflicts = cr.fetchall()
    if not conflicts:
        return
    details = ", ".join(f"{name} ({state})" for name, state in conflicts)
    raise UserError(
        "Cannot install module '%s' because this database already has conflicting %s modules: %s. "
        "Keep only one stack from this family installed per database."
        % (module_name, family_label, details)
    )


def pre_init_hook(env):
    _ensure_exclusive_modules(env, "om_account_followup", ACCOUNTING_STACK_B, "accounting stack")
