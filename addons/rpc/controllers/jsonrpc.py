from odoo.http import Controller, dispatch_rpc, route

from . import _check_request


class JSONRPC(Controller):
    @route('/jsonrpc', type='jsonrpc', auth="none", save_session=False)
    def jsonrpc(self, service, method, args):
        """ Method used by client APIs to contact OpenERP. """
        _check_request()
        return dispatch_rpc(service, method, args)
