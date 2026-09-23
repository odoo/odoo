from __future__ import annotations

import typing

from odoo.tools.safe_eval import safe_eval

from ..domain import Domain, DomainCondition, OptimizationLevel

if typing.TYPE_CHECKING:
    from .._typing import BaseModel, ModelLike
    from .environment import Environment

ACCESS_STORE_TABLES = "ir.model.access"
ACCESS_STORE_ROWS = "ir.access"


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


def _resolve_access_conditions(domain: Domain, model: BaseModel) -> Domain:
    def resolve(condition: DomainCondition) -> Domain:
        if condition.operator != "access":
            return condition
        return condition._optimize(model, OptimizationLevel.DYNAMIC_VALUES)

    return domain.map_conditions(resolve).optimize(model)


class IrAccessPolicy(AccessPolicy):
    __slots__ = ()

    def model_allowed(self, env: Environment, model_name: str, operation: str) -> bool:
        if env.su:
            return True
        model = env[model_name]
        domain = model._access_domain(operation)
        if domain.is_false():
            return False
        if not any(c.operator == "access" for c in domain.iter_conditions()):
            return True
        return not _resolve_access_conditions(domain, model.sudo()).is_false()

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


IR_ACCESS_POLICY = IrAccessPolicy()


class ModelRoutedAccessPolicy(AccessPolicy):
    # the store a model's decision is read from is the model's own choice
    # (`_access_store`) until every model is on ir.access
    __slots__ = ()

    @staticmethod
    def _routed(env: Environment, model_name: str) -> bool:
        model_class = env.registry.models.get(model_name)
        return (
            model_class is not None and model_class._access_store == ACCESS_STORE_ROWS
        )

    def model_allowed(self, env: Environment, model_name: str, operation: str) -> bool:
        if self._routed(env, model_name):
            return IR_ACCESS_POLICY.model_allowed(env, model_name, operation)
        return super().model_allowed(env, model_name, operation)

    def model_denied_error(
        self, env: Environment, model_name: str, operation: str
    ) -> Exception:
        if self._routed(env, model_name):
            return IR_ACCESS_POLICY.model_denied_error(env, model_name, operation)
        return super().model_denied_error(env, model_name, operation)

    def record_domain(
        self, env: Environment, model_name: str, operation: str
    ) -> Domain:
        if self._routed(env, model_name):
            return IR_ACCESS_POLICY.record_domain(env, model_name, operation)
        return super().record_domain(env, model_name, operation)

    def security_domain(
        self, env: Environment, model_name: str, operation: str
    ) -> Domain:
        if self._routed(env, model_name):
            return IR_ACCESS_POLICY.security_domain(env, model_name, operation)
        return super().security_domain(env, model_name, operation)

    def record_denied_error(
        self, env: Environment, operation: str, records: ModelLike
    ) -> Exception:
        if self._routed(env, records._name):
            return IR_ACCESS_POLICY.record_denied_error(env, operation, records)
        return super().record_denied_error(env, operation, records)


ACCESS_POLICY = ModelRoutedAccessPolicy()
