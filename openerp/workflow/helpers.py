import openerp.sql_db

class Session(object):
    def __init__(self, cr, uid):
        assert isinstance(cr, openerp.sql_db.Cursor)
        assert isinstance(uid, (int, long))
        self.cr = cr
        self.uid = uid

class Record(object):
    def __init__(self, model, record_id):
        assert isinstance(model, basestring)
        assert isinstance(record_id, (int, long))
        self.model = model
        self.id = record_id

class WorkflowActivity(object):
    KIND_FUNCTION = 'function'
    KIND_DUMMY = 'dummy'
    KIND_STOPALL = 'stopall'
    KIND_SUBFLOW = 'subflow'
