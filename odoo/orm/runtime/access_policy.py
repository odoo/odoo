from __future__ import annotations

import typing

from ..domain import Domain

if typing.TYPE_CHECKING:
    from .._typing import ModelLike
    from .environment import Environment


class AccessPolicy:
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

    def rule_context(self, env: Environment) -> tuple:
        if "ir.access" not in env.registry:
            company_ids = env.context.get("allowed_company_ids")
            return (tuple(company_ids) if company_ids else company_ids,)
        return tuple(env["ir.access"]._get_access_context())

    def record_denied_error(
        self, env: Environment, operation: str, records: ModelLike
    ) -> Exception:
        return env["ir.access"]._make_record_access_error(records, operation)

    def access_signature(self, env: Environment) -> tuple:
        return env["ir.access"]._policy_signature()

    def bound_access_rows(
        self, env: Environment, model_name: str, operation: str
    ) -> tuple[list[Domain], list[Domain]]:
        return env["ir.access"]._bound_access_rows(model_name, operation)


# every registry decides from the ir.access model it hosts; an in-memory one
# that hosts none raises its tier's marker the moment a principal is checked
ACCESS_POLICY = AccessPolicy()
