#----------------------------------------------------------
# OpenERPSession local openerp backend access
#----------------------------------------------------------
class OpenERPUnboundException(Exception):
    pass

class OpenERPConnector(object):
    pass

class OpenERPAuth(object):
    pass

class OpenERPModel(object):
    def __init__(self, session, model):
        self._session = session
        self._model = model

    def __getattr__(self, name):
        return lambda *l:self._session.execute(self._model, name, *l)

class OpenERPSession(object):
        def __init__(self, model_factory=OpenERPModel):
            pass
