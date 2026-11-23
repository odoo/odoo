from . import models
from . import wizard


def _post_init_hook(env):
    """Ensure every internal user is implicitly a Deduction User.

    The XML-level implication on base.group_user is unreliable when the
    base record is already heavily populated; this hook guarantees the
    implication is established on every install/upgrade.
    """
    base_user = env.ref('base.group_user', raise_if_not_found=False)
    ded_user = env.ref(
        'KSW_deduction.group_deduction_user', raise_if_not_found=False)
    if base_user and ded_user and ded_user not in base_user.implied_ids:
        base_user.sudo().write({'implied_ids': [(4, ded_user.id)]})
