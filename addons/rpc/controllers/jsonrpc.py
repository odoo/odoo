import logging

from odoo import SUPERUSER_ID, api
from odoo.http import Controller, dispatch_rpc, request, route
from odoo.modules.registry import Registry

from . import RPC_DEPRECATION_NOTICE, _check_request

logger = logging.getLogger(__name__)


class JSONRPC(Controller):
    @route('/jsonrpc', type='jsonrpc', auth="none", save_session=False)
    def jsonrpc(self, service, method, args):
        """ Method used by client APIs to contact OpenERP. """
        if service == 'object' or (service == 'common' and method in ('login', 'authenticate')):
            with Registry(args[0]).cursor(readonly=True) as cr:
                env = api.Environment(cr, SUPERUSER_ID, {})
                if not env['ir.config_parameter'].get_bool('rpc.use_deprecated_services'):
                    raise request.not_found()
        logger.warning(RPC_DEPRECATION_NOTICE, __name__)
        _check_request()
        return dispatch_rpc(service, method, args)
