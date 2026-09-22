from __future__ import annotations

import typing

if typing.TYPE_CHECKING:
    from .._typing import ModelLike
    from ..domain import Domain
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


ACCESS_POLICY = AccessPolicy()
