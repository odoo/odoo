# -*- coding: utf-8 -*-
from odoo.http import request
from odoo.service import common, db

def dispatch(func, *args):
    if func not in funcs:
        raise NameError("No global function %s" % func)

    fn = funcs[func]
    if getattr(fn, '__noadmin__', False):
       pass
    else:
        db.check_super(request.httprequest.authorization.password)
    return fn(*args)

funcs = {}
def register(fn):
    funcs[fn.__name__] = fn
    return fn
def noadmin(fn):
    fn.__noadmin__ = True
    return fn

@register
@noadmin
def version():
    return common.exp_version()

@register
def create(dbname, demo, lang, user_password='admin'):
    return db.exp_create_database(
        dbname, demo, lang, user_password=user_password)

@register
def drop(dbname):
    return db.exp_drop(dbname)

@register
def dump(dbname, format):
    return db.exp_dump(dbname, format)

@register
def restore(dbname, data, copy=False):
    return db.exp_restore(dbname, data, copy)

@register
def rename(old, new):
    return db.exp_rename(old, new)

@register
def change_admin_password(new):
    return db.exp_change_admin_password(new)

@register
def migrate_databases(databases):
    return db.exp_migrate_databases(databases)

@register
def duplicate(source, destination):
    return db.exp_duplicate_database(source, destination)

@register
@noadmin
def exists(dbname):
    return db.exp_db_exist(dbname)

@register
@noadmin
def list(document=False):
    return db.exp_list(document)

@register
@noadmin
def list_languages():
    return db.exp_list_lang()
