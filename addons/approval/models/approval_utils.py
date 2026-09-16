from typing import Any

from odoo.exceptions import UserError

from . import approval_trace as trace


class ApprovalStepUnstaffed(UserError):
    def __init__(self, message, step=None, company=None):
        super().__init__(message)
        self.step = step
        self.company = company


def is_approval_manager(env) -> bool:
    return env.user._is_approval_manager()


def boolean_search_domain(
    operator: str,
    value: Any,
    true_domain: Any,
    false_domain: Any,
) -> Any:
    if operator == "=":
        wants_true, wants_false = bool(value), not value
    elif operator == "!=":
        wants_true, wants_false = not value, bool(value)
    elif operator == "in":
        values = set(value or ())
        wants_true, wants_false = True in values, False in values
    elif operator == "not in":
        values = set(value or ())
        wants_true, wants_false = True not in values, False not in values
    else:
        raise NotImplementedError(f"Unsupported operator {operator!r}")

    if wants_true and wants_false:
        branch, domain = "both", []
    elif wants_true:
        branch, domain = "true", true_domain
    elif wants_false:
        branch, domain = "false", false_domain
    else:
        branch, domain = "neither", [("id", "=", False)]
    trace.SEARCH.event("boolean_domain", operator=operator, value=value, branch=branch)
    return domain
