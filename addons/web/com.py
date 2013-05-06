
import openerp.service.security as security
import openerp.service.model as model
import openerp

def _sessions():
    if getattr(_thread_data, "sessions", None) is None:
        _thread_data.sessions = []
    return _thread_data.sessions

class Session(object):
    def __init__(self, db, uid, password):
        self.db = db
        self.uid = uid
        self.password = password
        self.cr = None

    def model(self, model_name):
        return Model(self, model_name)

    def _execute(self, model_name, method, args, kwargs):
        self.ensure_transation()
        return model.execute_cr(self.cr, self.uid, model_name, method, *args, **kwargs)

    def ensure_transation(self):
        if self.cr is None:
            security.check(self.db, self.uid, self.password)
            threading.currentThread().dbname = self.db
            self.cr = openerp.registry(self.db).db.cursor()

    def close_transaction(self, has_exception=False):
        if self.cr is None:
            return
        if has_exception:
            try:
                self.cr.rollback()
            except:
                pass # nothing
        else:
            try:
                self.cr.commit()
            except:
                pass # nothing
        try:
            self.cr.close()
        except:
            pass # nothing
        self.cr = None

class Model(object):
    def __init__(self, session, name):
        self.session = session
        self.name = name

    def __getattr__(self, method):
        def proxy(*args, **kw):
            result = self.session._execute(self.name, method, args, kw)
            # reorder read
            if method == "read":
                if isinstance(result, list) and len(result) > 0 and "id" in result[0]:
                    index = {}
                    for r in result:
                        index[r['id']] = r
                    result = [index[x] for x in args[0] if x in index]
            return result
        return proxy

    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None, context=None):
        record_ids = self.search(domain or [], offset, limit or False, order or False, context or {})
        if not record_ids: return []
        records = self.read(record_ids, fields or [], context or {})
        return records

import threading
_thread_data = threading.local()

class _ThreadSession:
    def __getattr__(self, name):
        if len(_sessions()) == 0:
            raise Exception("Session not initialized")
        return getattr(_sessions()[-1], name)
    def __setattr__(self, name, value):
        if len(_sessions()) == 0:
            raise Exception("Session not initialized")
        return setattr(_sessions()[-1], name, value)
    def init(self, db, uid, password):
        ses = self
        class with_obj:
            def __enter__(self):
                _sessions().append(Session(db, uid, password))
            def __exit__(self, type, value, traceback):
                _sessions().pop().close_transaction(type is not None)
        return with_obj()

transaction = _ThreadSession()