# Part of Odoo. See LICENSE file for full copyright and licensing details.

import collections.abc
import inspect
from odoo.service import common, db
from .exceptions import RpcError, RpcErrorCode

_functions = {}
def register(*, admin_only):
    def register_(fn):
        fn.admin_only = admin_only
        _functions[fn.__name__.rstrip('_')] = fn
        return fn
    return register_

def dispatch(function_name, *params, admin_password=None):
    args, kwargs = extract_call_info(params)
    function = find_function(function_name, args, kwargs)
    if function.admin_only:
        db.check_super(admin_password)
    return function(*args, **kwargs)

def extract_call_info(params):
    params = params or ({},)

    if len(params) > 1:
        suggestion = {'args': list(params)}
        raise RpcError(RpcErrorCode.invalid_params) from TypeError(
            "the RPC2 endpoint takes a single parameter: a dict with "
            "args and kwargs (both optional) keys. Did you mean "
            f"{suggestion}?")

    if (not isinstance(params[0], collections.abc.Mapping)
     or not {'args', 'kwargs'}.issuperset(params[0].keys())):
        raise RpcError(RpcErrorCode.invalid_params) from TypeError(
            "the RPC2 endpoint takes a single parameter: a dict with "
            "args and kwargs (both optional) keys")

    return params[0].get('args', []), params[0].get('kwargs', {})

def find_function(function_name, args, kwargs):
    try:
        function = _functions[function_name]
    except KeyError as exc:
        err = NameError(f"no admin function {function_name!r} found")
        err.__cause__ = exc
        raise RpcError(RpcErrorCode.method_not_found) from err
    try:
        inspect.signature(function).bind(*args, **kwargs)
    except TypeError as exc:
        raise RpcError(RpcErrorCode.invalid_params) from exc
    return function


@register(admin_only=False)
def login(db, login, password):
    return common.exp_authenticate(db, login, password, None)


@register(admin_only=False)
def authenticate(db, login, password, user_agent_env):
    return common.exp_authenticate(db, login, password, user_agent_env)


@register(admin_only=False)
def version():
    return common.exp_version()


@register(admin_only=True)
def create(dbname, demo, lang, user_password='admin'):
    return db.exp_create_database(
        dbname, demo, lang, user_password=user_password)


@register(admin_only=True)
def drop(dbname):
    return db.exp_drop(dbname)


@register(admin_only=True)
def dump(dbname, frmt):
    return db.exp_dump(dbname, frmt)


@register(admin_only=True)
def restore(dbname, data, copy=False):
    return db.exp_restore(dbname, data, copy)


@register(admin_only=True)
def rename(old, new):
    return db.exp_rename(old, new)


@register(admin_only=True)
def change_admin_password(new):
    return db.exp_change_admin_password(new)


@register(admin_only=True)
def migrate_databases(databases):
    return db.exp_migrate_databases(databases)


@register(admin_only=True)
def duplicate(source, destination):
    return db.exp_duplicate_database(source, destination)


@register(admin_only=False)
def exists(dbname):
    return db.exp_db_exist(dbname)


@register(admin_only=False)
def list_(document=False):
    return db.exp_list(document)


@register(admin_only=False)
def list_languages():
    return db.exp_list_lang()


del register
