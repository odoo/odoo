# -*- coding: utf-8 -*-
import itertools

import odoo.api
import odoo.exceptions

def dispatch(registry, uid, model, method, *args):
    ids, context, args, kwargs = extract_call_info(method, args)

    with registry.cursor() as cr:
        env = odoo.api.Environment(cr, uid, context or {})
        records = env[model].browse(ids)
        return getattr(records, method)(*args, **kwargs)


def extract_call_info(method, args):
    if method.startswith('_'):
        raise odoo.exceptions.AccessError(
            "%s is a private method and can not be called over RPC" % method)
    subject, args, kwargs = itertools.islice(
        itertools.chain(args, [None, None, None]),
        0, 3)
    ids = []
    context = {}
    # comes straight from xmlrpclib.loads, so should only be list or dict
    if type(subject) is list:
        ids = subject
    elif type(subject) is dict:
        ids = subject.get('records')
        context = subject.get('context')
    elif subject:
        # other truthy subjects are errors
        raise ValueError("Unknown RPC subject %s, expected falsy value, list or dict" % subject)

    # optional args, kwargs
    if type(args) is dict:
        kwargs = args
        args = None
    if args is None: args = []
    if kwargs is None: kwargs = {}

    return ids, context, args, kwargs
