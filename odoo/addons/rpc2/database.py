# -*- coding: utf-8 -*-
def dispatch(registry, uid, func, *args):
    raise NameError("No function %s in database %s" % (func, registry.db_name))
