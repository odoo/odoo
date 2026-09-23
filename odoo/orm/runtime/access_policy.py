from __future__ import annotations

import typing

from odoo.tools.safe_eval import safe_eval

from ..domain import Domain

if typing.TYPE_CHECKING:
    from .._typing import ModelLike
    from .environment import Environment

class AccessPolicy:
    __slots__ = ()

    def model_allowed(self, env: Environment, model_name: str, operation: str) -> bool:
        return env["ir.model.access"].check(
            model_name, operation, raise_exception=False
        )

    def model_denied_error(
        self, env: Environment, model_name: str, operation: str
    ) -> Exception:
        return env["ir.model.access"]._prepare_access_error(model_name, operation)

    def record_domain(
        self, env: Environment, model_name: str, operation: str
    ) -> Domain:
        return env["ir.rule"]._get_domain_accessible_records(model_name, operation)

    def security_domain(
        self, env: Environment, model_name: str, operation: str
    ) -> Domain:
        if env.su:
            return Domain.TRUE
        if not self.model_allowed(env, model_name, operation):
            return Domain.FALSE
        return self.record_domain(env, model_name, operation)

    def rule_context(self, env: Environment) -> tuple:
        try:
            rules = env["ir.rule"]
        except NotImplementedError:
            return ()
        values = getattr(rules, "_get_context_values_in_domains", None)
        if values is None:
            company_ids = env.context.get("allowed_company_ids")
            return (tuple(company_ids) if company_ids else company_ids,)
        return tuple(values())

    def record_denied_error(
        self, env: Environment, operation: str, records: ModelLike
    ) -> Exception:
        return env["ir.rule"]._prepare_access_error(operation, records)

    def access_signature(self, env: Environment) -> tuple:
        return env["ir.access"]._policy_signature()

    def bound_access_rows(
        self, env: Environment, model_name: str, operation: str
    ) -> tuple[list[Domain], list[Domain]]:
        # the domains of the ir.access permissions the principal's groups hold
        # and of the guards that bind it, for one model and operation
        store = env["ir.access"]
        letter = store._operation_letter(operation)
        group_ids = set(env.user._get_group_ids())
        permissions: list[Domain] = []
        guards: list[Domain] = []
        eval_context = None
        for row in store._get_all_access().get(model_name, ()):
            if letter not in row.operation:
                continue
            binds = row.kind == "guard" and row.guard_scope == "everyone"
            if not binds and row.group_id not in group_ids:
                continue
            domain = row.domain
            if not isinstance(domain, Domain):
                if eval_context is None:
                    eval_context = store._eval_context()
                domain = Domain(safe_eval(domain, eval_context))
            (permissions if row.kind == "permission" else guards).append(domain)
        return permissions, guards


class IrAccessPolicy(AccessPolicy):
    __slots__ = ()

    def model_allowed(self, env: Environment, model_name: str, operation: str) -> bool:
        return env.su or env[model_name]._access_allowed(operation)

    def model_denied_error(
        self, env: Environment, model_name: str, operation: str
    ) -> Exception:
        return env["ir.access"]._make_model_access_error(model_name, operation)

    def record_domain(
        self, env: Environment, model_name: str, operation: str
    ) -> Domain:
        if env.su:
            return Domain.TRUE
        return env[model_name]._access_domain(operation)

    def security_domain(
        self, env: Environment, model_name: str, operation: str
    ) -> Domain:
        return self.record_domain(env, model_name, operation)

    def record_denied_error(
        self, env: Environment, operation: str, records: ModelLike
    ) -> Exception:
        return env["ir.access"]._make_record_access_error(records, operation)


# a database registry decides every model from ir.access; an in-memory one
# answers through whichever ir.model.access and ir.rule classes it hosts,
# which on a host of base's own models ends in the same decision
ACCESS_POLICY = IrAccessPolicy()
HOSTED_ACCESS_POLICY = AccessPolicy()
