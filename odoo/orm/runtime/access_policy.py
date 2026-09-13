from __future__ import annotations

import typing

if typing.TYPE_CHECKING:
    from .._typing import BaseModel
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

    def record_denied_error(
        self, env: Environment, operation: str, records: BaseModel
    ) -> Exception:
        return env["ir.rule"]._prepare_access_error(operation, records)


ACCESS_POLICY = AccessPolicy()
