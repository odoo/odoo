from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import TYPE_CHECKING, Any, Protocol, cast, runtime_checkable

if TYPE_CHECKING:
    from types import MethodType

    import werkzeug.datastructures
    import werkzeug.routing

    import odoo.api
    from odoo.modules.registry import Registry

    from ._cookies import FutureResponse
    from .dispatcher import Dispatcher
    from .geoip import GeoIP
    from .session import Session
    from .wrappers import HTTPRequest, Response


if TYPE_CHECKING:

    class RequestState:
        app: Any
        database_detached: bool
        db: str | None
        dispatcher: Dispatcher
        env: odoo.api.Environment | None
        future_response: FutureResponse
        geoip: GeoIP
        httprequest: HTTPRequest
        params: dict[str, Any]
        _params_source: Callable[[], dict[str, Any]] | None
        registry: Registry | None
        session: Session
        _session_response: Response | None
        _session_snapshot: Session | None
        _session_transaction_cursor: Any
        _session_written_in_transaction: bool
        _session_max_age: int | None
        _session_save_pending: bool

        def get_default_lang(self) -> str: ...

        def _select_session_and_dbname(
            self, sid: str | None = None
        ) -> tuple[Session, str | None]: ...

        def _update_response_from_future(self, response: Response) -> Response: ...

        def _reset_for_replay(self, cr: Any = None) -> None: ...

        def _save_session(self, env: odoo.api.Environment | None = None) -> None: ...

        def _bind_session_transaction(self, cr: Any) -> None: ...

        def _restore_session_snapshot(self) -> None: ...

        def _flush_session(self) -> None: ...

        def get_http_params(self) -> dict[str, Any]: ...

        def get_json_data(self) -> Any: ...

        def prepare_json_response(
            self,
            data: Any,
            headers: list[tuple[str, str]] | None = None,
            cookies: Mapping[str, str] | None = None,
            status: int = 200,
        ) -> Response: ...

        def redirect(
            self, location: str, code: int = 303, local: bool = True
        ) -> Response: ...

        def redirect_query(
            self,
            location: str,
            query: dict[str, str] | None = None,
            code: int = 303,
            local: bool = True,
        ) -> Response: ...

        def is_valid_csrf(self, csrf: str | None) -> bool: ...

else:
    RequestState = object


class HasRouting(Protocol):
    routing: Mapping[str, Any]


class RoutedMethod(Protocol):
    original_routing: Mapping[str, Any]
    original_endpoint: Callable

    def __call__(self, *args: Any, **kwargs: Any) -> Any: ...


class Endpoint(HasRouting, RoutedMethod, Protocol):
    func: MethodType
    _param_specs: dict[str, Any] | None
    typed_list_params: frozenset[str] | None


@runtime_checkable
class HttpExtension(Protocol):
    def routing_map(self, key: str | None = None) -> werkzeug.routing.Map:
        pass

    def _match(self, path_info: str) -> tuple[werkzeug.routing.Rule, dict[str, Any]]:
        pass

    def _dispatch(self, endpoint: Callable) -> Any:
        pass

    def _authenticate(self, endpoint: Callable) -> None:
        pass

    def _authenticate_explicit(self, auth: str) -> None:
        pass

    def _pre_dispatch(
        self,
        rule: werkzeug.routing.Rule,
        args: dict[str, Any],
    ) -> None:
        pass

    def _post_dispatch(self, response: Response) -> None:
        pass

    def _handle_error(self, exception: Exception) -> Response:
        pass

    def _serve_fallback(self) -> Response | None:
        pass

    def _redirect(self, location: str, code: int = 303) -> Response:
        pass

    def _is_allowed_cookie(self, cookie_type: str) -> bool:
        pass

    def _update_cookies(
        self,
        cookies: werkzeug.datastructures.MultiDict,
    ) -> None:
        pass

    def _post_logout(self) -> None:
        pass

    def _apply_max_upload_size(self) -> None:
        pass


def get_ir_http(source: Registry | odoo.api.Environment) -> HttpExtension:
    return cast("HttpExtension", source["ir.http"])
