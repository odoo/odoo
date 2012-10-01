# -*- coding: utf-8 -*-

from ..common import http, nonliterals
from ..controllers.main import Session

UID = 87539319
DB = 'test_db'
LOGIN = 'test_login'
PASSWORD = 'test_password'
CONTEXT = {'lang': 'en_US', 'tz': 'UTC', 'uid': UID}

def bind(session):
    session.bind(DB, UID, LOGIN, PASSWORD)
    session.context = CONTEXT
    session.build_connection().set_login_info(DB, LOGIN, PASSWORD, UID)

class TestController(http.Controller):
    _cp_path = '/tests'

    @http.jsonrequest
    def add_nonliterals(self, req, domains, contexts):
        return {
            'domains': [nonliterals.Domain(req.session, domain)
                        for domain in domains],
            'contexts': [nonliterals.Context(req.session, context)
                         for context in contexts]
        }

class TestSession(Session):
    _cp_path = '/web/session'

    def session_info(self, req):
        if not req.session._uid:
            bind(req.session)

        return {
            "session_id": req.session_id,
            "uid": req.session._uid,
            "context": CONTEXT,
            "db": req.session._db,
            "login": req.session._login,
        }
