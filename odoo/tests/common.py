import contextlib
import datetime
import importlib
import logging
import unittest
from collections import defaultdict
from functools import wraps
from typing import TYPE_CHECKING, Any
from unittest.mock import patch

import freezegun
from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import ed25519

import odoo.cli
from odoo import api
from odoo.fields import Command
from odoo.libs.debug_log import DebugLog
from odoo.tools import (
    config,
    mute_logger,
)
from odoo.tools.cache import _COUNTERS
from odoo.tools.mail import single_email_re
from odoo.tools.xml_utils import _check_xml

from .browser import ChromeBrowser, ChromeBrowserException
from .case import TestCase
from .matchers import Like, RecordCapturer, WhitespaceInsensitive
from .transaction_case import (
    TEST_CURSOR_COOKIE_NAME,
    BaseCase,
    SingleTransactionCase,
    TransactionCase,
    _registry_test_lock,
    gc_test_filestore,
    release_stranded_test_cursors,
    release_test_lock,
)
from .utils import HOST, get_db_name, save_test_file

if TYPE_CHECKING:
    from collections.abc import Callable

    from .http import HttpCase, JsonRpcException, Opener, Transport


__all__ = [
    "ADMIN_USER_ID",
    "HOST",
    "TEST_CURSOR_COOKIE_NAME",
    "BaseCase",
    "ChromeBrowser",
    "ChromeBrowserException",
    "Command",
    "HttpCase",
    "JsonRpcException",
    "Like",
    "Opener",
    "RecordCapturer",
    "SingleTransactionCase",
    "TransactionCase",
    "Transport",
    "WhitespaceInsensitive",
    "can_import",
    "freeze_time",
    "gc_test_filestore",
    "get_cache_key_counter",
    "get_db_name",
    "loaded_demo_data",
    "mute_logger",
    "new_test_user",
    "no_retry",
    "patch",
    "release_stranded_test_cursors",
    "release_test_lock",
    "save_test_file",
    "skip_if_dev_mode",
    "standalone",
    "standalone_tests",
    "tagged",
    "test_xsd",
    "users",
    "warmup",
]

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)
_debug.lifecycle(
    "test.framework.imported",
    command=odoo.cli.COMMAND,
    test_enable=bool(config["test_enable"]),
)
if odoo.cli.COMMAND in ("server", "start") and not config["test_enable"]:
    _logger.error(
        "Importing test framework, avoid importing from business modules and when not running in test mode",
        stack_info=True,
    )
else:
    _logger.info(
        "Importing test framework",
        stack_info=_logger.isEnabledFor(logging.DEBUG),
    )


def get_cache_key_counter(bound_method, *args, **kwargs):
    model = bound_method.__self__
    ormcache_instance = bound_method.__cache__
    cache = model.pool.ormcache_lrus[ormcache_instance.cache_name]
    key = ormcache_instance.key(model, *args, **kwargs)
    counter = _COUNTERS[model.pool.db_name, ormcache_instance.method]
    _debug.logic(
        "test.cache.key_counter",
        model=model._name,
        cache=ormcache_instance.cache_name,
        method=getattr(ormcache_instance.method, "__name__", None),
        hit=counter.hit,
        miss=counter.miss,
    )
    return cache, key, counter


ADMIN_USER_ID = api.SUPERUSER_ID


def skip_if_dev_mode(*flags: str) -> None:
    dev_mode = config["dev_mode"]
    if active := [flag for flag in flags if flag in dev_mode]:
        _debug.logic("test.case.dev_mode_skip", flags=active)
        raise unittest.SkipTest(
            f"--dev={','.join(active)} disables the behaviour under test"
        )


standalone_tests: defaultdict[str, list] = defaultdict(list)


_registry_test_lock.acquire()
_debug.lifecycle("test.lock.acquired_at_import", held=_registry_test_lock.count)


def standalone(*tags: str) -> Callable[[Callable], Callable]:

    def register(func: Callable) -> Callable:
        module = None
        if func.__module__.startswith("odoo.addons."):
            module = func.__module__.split(".")[2]
            standalone_tests[module].append(func)
        for tag in tags:
            standalone_tests[tag].append(func)
        standalone_tests["all"].append(func)
        _debug.lifecycle(
            "test.standalone.registered",
            func=func.__qualname__,
            module=module,
            tags=list(tags),
            total=len(standalone_tests["all"]),
        )
        return func

    return register


def test_xsd(url=None, path=None, skip=False, xsd_name=None):
    def decorator(func):
        @wraps(func)
        def wrapped_f(self, *args, **kwargs):
            if skip:
                _debug.logic("test.xsd.skipped", func=func.__qualname__)
                raise unittest.SkipTest(
                    skip if isinstance(skip, str) else "XSD validation disabled"
                )
            xmls = func(self, *args, **kwargs)
            with _debug.perf(
                "test.xsd.check",
                cr=self.env.cr,
                func=func.__qualname__,
                xsd=xsd_name,
                url=url is not None,
                path=path is not None,
                documents=len(xmls) if isinstance(xmls, (list, tuple)) else 1,
            ):
                _check_xml(self.env, url, path, xmls, xsd_name)

        return wrapped_f

    return decorator


def new_test_user(env, login="", groups="base.group_user", context=None, **kwargs):
    if not login:
        raise ValueError("New users require at least a login")
    if not groups:
        raise ValueError("New users require at least user groups")
    if context is None:
        context = {}

    group_ids = [
        Command.set(
            kwargs.pop("group_ids", False)
            or [env.ref(g.strip()).id for g in groups.split(",")]
        )
    ]
    create_values = dict(kwargs, login=login, group_ids=group_ids)
    if not create_values.get("name"):
        create_values["name"] = f"{login} ({groups})"
    if not create_values.get("password"):
        create_values["password"] = login + "x" * (8 - len(login))
    if "email" not in create_values:
        if single_email_re.match(login):
            create_values["email"] = login
        else:
            create_values["email"] = f"{login[0]}.{login[0]}@example.com"
    if "company_id" in create_values and "company_ids" not in create_values:
        create_values["company_ids"] = [(4, create_values["company_id"])]
    # the user reads in the language and dates in the zone of the environment the
    # test runs in, not in whatever ir.default an installed module gives new partners
    create_values.setdefault(
        "lang", context.get("lang") or env.context.get("lang") or "en_US"
    )
    create_values.setdefault("tz", context.get("tz") or env.context.get("tz") or False)

    with _debug.perf(
        "test.user.create",
        cr=env.cr,
        login=login,
        groups=groups,
        keys=sorted(create_values),
        context=sorted(context),
    ) as span:
        user = env["res.users"].with_context(**context).create(create_values)
        span.set(uid=user.id)
    return user


def loaded_demo_data(env: api.Environment) -> bool:
    loaded = bool(env.ref("base.user_demo", raise_if_not_found=False))
    _debug.logic("test.env.demo_data", loaded=loaded)
    return loaded


def no_retry(arg: Any) -> Any:
    arg._retry = False
    _debug.lifecycle("test.case.no_retry", target=getattr(arg, "__qualname__", None))
    return arg


def users(*logins: str) -> Callable:
    assert logins, "Expecting at least one login to execute"

    def users_decorator(func: Callable, /) -> Callable:
        @wraps(func)
        def with_users(self: Any, *args: Any, **kwargs: Any) -> None:
            old_uid = self.uid
            _debug.pipeline(
                "test.users.run", func=func.__qualname__, logins=len(logins)
            )
            try:
                Users = self.env["res.users"].with_context(active_test=False)
                user_id = {
                    user.login: user.id
                    for user in Users.search([("login", "in", list(logins))])
                }
                missing = [login for login in logins if login not in user_id]
                if missing:
                    _debug.logic("test.users.missing", missing=missing)
                assert not missing, f"No user with login {missing}"
                for login in logins:
                    with self.subTest(login=login):
                        self.uid = user_id[login]
                        _debug.lifecycle(
                            "test.users.as", login=login, uid=user_id[login]
                        )
                        with _debug.perf("test.users.body", cr=self.cr, login=login):
                            func(self, *args, **kwargs)
                            self.env.flush_all()
                    self.env.invalidate_all()
            finally:
                self.uid = old_uid

        return with_users

    return users_decorator


def warmup(func: Callable, /) -> Callable:

    @wraps(func)
    def warmup(self: Any, *args: Any, **kwargs: Any) -> None:
        self.env.flush_all()
        self.env.invalidate_all()
        self.warm = False
        # Two cold passes. Recomputing an ormcached method loads records as a side
        # effect, so the pass that fills the ormcache does not take the path the
        # steady state takes: it finds in the record cache what a later run has to
        # fetch, and never caches what that fetch needs (the rule domain of the
        # model, say). Whether the first pass recomputes depends on what ran
        # before the test, which made a pinned count read one higher inside a
        # suite than alone. The second pass starts from a full ormcache and an
        # empty record cache, like the measured one.
        for cold_pass in (1, 2):
            with (
                _debug.perf(
                    "test.warmup.cold",
                    cr=self.cr,
                    func=func.__qualname__,
                    cold_pass=cold_pass,
                ),
                contextlib.closing(self.cr.savepoint(flush=False)),
            ):
                func(self, *args, **kwargs)
                self.env.flush_all()
            self.env.invalidate_all()
        self.warm = True
        with _debug.perf("test.warmup.warm", cr=self.cr, func=func.__qualname__):
            func(self, *args, **kwargs)

    return warmup


def can_import(module: str) -> bool:
    try:
        importlib.import_module(module)
    except ImportError:
        _debug.logic("test.import.probe", module=module, ok=False)
        return False
    else:
        _debug.logic("test.import.probe", module=module, ok=True)
        return True


def tagged(*tags: str) -> Callable:
    include = {t for t in tags if not t.startswith("-")}
    exclude = {t[1:] for t in tags if t.startswith("-")}

    def tags_decorator(target: Any) -> Any:
        obj: Any = target
        if not isinstance(target, type):
            obj.test_tags = getattr(obj, "test_tags", set()) | include
            obj.test_tags_exclude = getattr(obj, "test_tags_exclude", set()) | exclude
            _debug.lifecycle(
                "test.tags.applied",
                kind="method",
                target=getattr(obj, "__qualname__", None),
                include=sorted(include),
                exclude=sorted(exclude),
            )
            return obj

        obj.test_tags = (getattr(obj, "test_tags", set()) | include) - exclude
        at_install = "at_install" in obj.test_tags
        post_install = "post_install" in obj.test_tags
        _debug.lifecycle(
            "test.tags.applied",
            kind="class",
            target=obj.__qualname__,
            include=sorted(include),
            exclude=sorted(exclude),
            tags=sorted(obj.test_tags),
        )
        if not (at_install ^ post_install):
            _debug.logic(
                "test.tags.position_ambiguous",
                target=obj.__qualname__,
                at_install=at_install,
                post_install=post_install,
            )
            _logger.warning(
                "A tests should be either at_install or post_install, which is not the case of %r",
                obj,
            )
        return obj

    return tags_decorator


def _bind_cryptography_to_the_real_datetime() -> None:
    key = ed25519.Ed25519PrivateKey.generate()
    name = x509.Name([])
    epoch = datetime.datetime(2000, 1, 1, tzinfo=datetime.UTC)
    (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(1)
        .not_valid_before(epoch)
        .not_valid_after(epoch)
        .sign(key, None)
    )


_bind_cryptography_to_the_real_datetime()


class freeze_time:
    _freeze_time = staticmethod(freezegun.freeze_time)

    def __init__(
        self,
        time_to_freeze: Any = None,
        tz_offset: int = 0,
        ignore: list[str] | None = None,
        tick: bool = False,
        as_arg: bool = False,
        as_kwarg: str = "",
        auto_tick_seconds: float = 0,
        real_asyncio: bool = False,
    ) -> None:
        self.freezer = self._freeze_time(
            time_to_freeze=time_to_freeze,
            tz_offset=tz_offset,
            # freezegun patches time.perf_counter too; the campaign's perf spans
            # (odoo/libs/debug_log.py) must keep the real clock or a span that
            # brackets a freeze reads the frozen epoch minus wall time.
            ignore=[*(ignore or ()), "odoo.libs.debug_log"],  # debuglog
            tick=tick,
            as_arg=as_arg,
            as_kwarg=as_kwarg,
            auto_tick_seconds=auto_tick_seconds,
            real_asyncio=real_asyncio,
        )

    def __call__(self, arg: Any) -> Any:
        target: Any = arg
        if isinstance(arg, type) and issubclass(arg, TestCase):
            target.freeze_time = self
            _debug.lifecycle(
                "test.freeze.bound", kind="class", target=target.__qualname__
            )
            return target

        _debug.lifecycle(
            "test.freeze.bound",
            kind="callable",
            target=getattr(arg, "__qualname__", type(arg).__name__),
        )
        return self.freezer(arg)

    def __enter__(self) -> Any:
        _debug.lifecycle("test.freeze.start")
        return self.freezer.start()

    def __exit__(self, *args: object) -> None:
        self.freezer.stop()
        _debug.lifecycle("test.freeze.stop")

    start = __enter__
    stop = __exit__


freezegun.freeze_time = freeze_time  # type: ignore[assignment]

_HTTP_EXPORTS = ("HttpCase", "JsonRpcException", "Opener", "Transport")
"""Names this module publishes on behalf of :mod:`odoo.tests.http`."""


def __getattr__(name: str) -> Any:
    if name in _HTTP_EXPORTS:
        from . import http

        globals().update({export: getattr(http, export) for export in _HTTP_EXPORTS})
        _debug.lifecycle("test.framework.http_exports_loaded", requested=name)
        return globals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted({*globals(), *_HTTP_EXPORTS})
