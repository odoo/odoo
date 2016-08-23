from openerp.osv import orm
from openerp.addons.connector.connector import ConnectorEnvironment
from openerp.addons.connector.checkpoint import checkpoint


def add_checkpoint(session, model_name, record_id, backend_id):
    """ Add a row in the model ``connector.checkpoint`` for a record,
    meaning it has to be reviewed by a user.

    :param session: current session
    :type session: :py:class:`openerp.addons.connector.session.ConnectorSession`
    :param model_name: name of the model of the record to be reviewed
    :type model_name: str
    :param record_id: ID of the record to be reviewed
    :type record_id: int
    :param backend_id: ID of the Prestashop Backend
    :type backend_id: int
    """
    return checkpoint.add_checkpoint(session, model_name, record_id,
                                     'prestashop.backend', backend_id)

def get_environment(session, model_name, backend_id):
    model = session.pool.get('prestashop.backend')
    backend_record = model.browse(session.cr,
                                  session.uid,
                                  backend_id,
                                  session.context)
    return ConnectorEnvironment(backend_record, session, model_name)
