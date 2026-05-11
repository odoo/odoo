import logging
from collections.abc import Iterable
from typing import Literal, NamedTuple, get_args

from odoo.http.routing_map import Controller

from odoo.addons.mail.tools.discuss import Store

_logger = logging.getLogger(__name__)

AUDIENCE = Literal["everyone", "logged_in", "internal"]
ALLOWED_AUDIENCE = get_args(AUDIENCE)


class StoreHandler(NamedTuple):
    audience: AUDIENCE
    func_name: str
    readonly: bool


class StoreHandlerRegistry:
    _items: dict[str, StoreHandler]

    def __init__(self):
        self._items = {}

    def add(
        self,
        name: str,
        func_name: str,
        *,
        audience: AUDIENCE = "internal",
        readonly: bool = False,
    ):
        assert audience in ALLOWED_AUDIENCE, (
            f'Invalid audience "{audience}" for store handler "{name}"'
        )
        assert name not in self._items, (
            f'Store handler "{name}" already registered with a different function: existing "{self._items[name].func_name}", received "{func_name}"'
        )
        self._validate_func_name(func_name)
        self._items[name] = StoreHandler(audience=audience, func_name=func_name, readonly=readonly)

    def execute_for_user(self, controller: Controller, store: Store, fetch_params: Iterable | str):
        for fetch_param in fetch_params:
            name, params, data_id = self._parse_fetch_param(fetch_param)
            store.data_id = data_id
            try:
                if not (entry := self._items.get(name)):
                    _logger.warning('No store handler registered for "%s"', name)
                    continue
                user = controller.env.user
                if (
                    entry.audience == "everyone"
                    or (entry.audience == "logged_in" and not user._is_public())
                    or (entry.audience == "internal" and user._is_internal())
                ):
                    assert isinstance(controller, Controller), (
                        "controller must be an instance of odoo.http.routing_map.Controller"
                    )
                    self._validate_func_name(entry.func_name)
                    # getattr: used to ensure we get the inherited method when the controller is extended,
                    # controller must be a Controller instance and func_name must start with "store_".
                    handler = getattr(controller, entry.func_name)
                    if params is None:
                        handler(store)
                    elif isinstance(params, dict):
                        handler(store, **params)
                    elif isinstance(params, list):
                        handler(store, *params)
                    else:
                        handler(store, params)
                else:
                    _logger.warning('User does not have access to store handler "%s"', name)
            finally:
                store.data_id = None

    def is_fetch_readonly(self, fetch_params: Iterable | str) -> bool:
        for fetch_param in fetch_params:
            name, _, _ = self._parse_fetch_param(fetch_param)
            if (entry := self._items.get(name)) and not entry.readonly:
                return False
        return True

    @staticmethod
    def _parse_fetch_param(param: str | tuple) -> tuple[str, any, int | None]:
        return (param, None, None) if isinstance(param, str) else (param + [None, None])[:3]

    @staticmethod
    def _validate_func_name(func_name):
        assert func_name.startswith("store_"), (
            f'Store handler function name must start with "store_", received "{func_name}"'
        )


store_handler_registry = StoreHandlerRegistry()


def store_handler(name: str, *, audience: AUDIENCE = "internal", readonly: bool = True):
    def store_handler__decorator(func):
        store_handler_registry.add(
            name,
            func.__name__,
            audience=audience,
            readonly=readonly,
        )
        return func

    return store_handler__decorator
