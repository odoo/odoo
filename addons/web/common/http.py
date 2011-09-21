# -*- coding: utf-8 -*-

import contextlib

import werkzeug.contrib.sessions

STORES = {}

@contextlib.contextmanager
def session(request, storage_path, session_cookie='sessionid'):
    session_store = STORES.get(storage_path)
    if not session_store:
        session_store = werkzeug.contrib.sessions.FilesystemSessionStore(
            storage_path)
        STORES[storage_path] = session_store

    sid = request.cookies.get(session_cookie)
    if sid:
        request.session = session_store.get(sid)
    else:
        request.session = session_store.new()

    try:
        yield request.session
    finally:
        session_store.save(request.session)
