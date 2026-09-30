import logging

from odoo.http import Controller, dispatch_rpc, route

from . import RPC_DEPRECATION_NOTICE, _check_request

logger = logging.getLogger(__name__)


class JSONRPC(Controller):
    @route('/jsonrpc', type='jsonrpc', auth="none", save_session=False)
    def jsonrpc(self, service, method, args):
        """ Method used by client APIs to contact OpenERP. """
        logger.warning(RPC_DEPRECATION_NOTICE, __name__)
        _check_request()
        return dispatch_rpc(service, method, args)
