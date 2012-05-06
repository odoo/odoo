# -*- coding: utf-8 -*-
import logging

try:
    import openerp.addons.web.common.http as openerpweb
except ImportError:
    import web.common.http as openerpweb

class PointOfSaleController(openerpweb.Controller):
    _cp_path = '/pos'

    @openerpweb.jsonrequest
    def dispatch(self, request, iface, **kwargs):
        method = 'iface_%s' % iface
        return getattr(self, method)(request, **kwargs)

    def iface_light(self, request, status):
        return True

    @openerpweb.jsonrequest
    def scan_item_success(self, request):
        """
        A product has been scanned with success
        """
        return False

    @openerpweb.jsonrequest
    def scan_item_error_unrecognized(self, request):
        """
        A product has been scanned without success
        """
        return False

    @openerpweb.jsonrequest
    def do_help(self, request, status):
        if status == 1:
            return help_needed(request)
        else:
            return help_cancelled(request)

    @openerpweb.jsonrequest
    def help_needed(self, request):
        """
        The user wants an help (ex: light is on)
        """
        return self.signal_help(request, status=True)

    @openerpweb.jsonrequest
    def help_cancelled(self, request):
        """
        The user stops the help request
        """
        return self.signal_help(request, status=False)

    #@openerpweb.jsonrequest
    #def weighting_start(self, request):
    #    return False

    #@openerpweb.jsonrequest
    #def weighting_read_kg(self, request):
    #    return 0.0

    #@openerpweb.jsonrequest
    #def weighting_end(self, request):
    #    return False

    #openerpweb.jsonrequest
    def do_weighting(self, request):
        # Start the weighting

        # Wait for 10 sec
        # IDEA: Thread, Signal ?

        # return a dict with the value or the error

        return {'weight' : 0.5}
        

    def do_payment(self, request, price, method, info):
        #return {'status' : 'ACCEPTED', 'reason' : ''}
        return {'status' : 'REFUSED', 'reason' : 'Payment blocked'}

    #@openerpweb.jsonrequest
    #def payment_request(self, request, price, method, info):
    #    """
    #    The PoS will activate the method payment 
    #    """
    #    return False

    #@openerpweb.jsonrequest
    #def is_payment_accepted(self, request):
    #    return False

    #@openerpweb.jsonrequest
    #def payment_cancelled(self, request):
    #    return False

    @openerpweb.jsonrequest
    def transaction_start(self, request):
        return False

    @openerpweb.jsonrequest
    def transaction_end(self, request):
        return False

    @openerpweb.jsonrequest
    def cashier_mode_activated(self, request):
        return False

    @openerpweb.jsonrequest
    def cashier_mode_deactivated(self, request):
        return False

