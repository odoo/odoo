# -*- coding: utf-8 -*-

import functools
import openerp


def download_file(f):
    """
    Decorator for actions which return a file in the action dict.

    If there is a 'file' in the dict, take it and save it in cache,
    so it doesn't get sent to the client. Otherwise, return the dict untouched.
    """

    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        rv = f(*args, **kwargs)

        if rv.get('type') == 'ir.actions.download':
            cr, uid = args[1:3]
            pool = openerp.registry(cr.dbname)
            download_id = pool['ir.actions.download']._add_download(uid, rv)
            rv = {
                'type': 'ir.actions.download',
                'download_id': download_id,
            }
        return rv

    return wrapper
