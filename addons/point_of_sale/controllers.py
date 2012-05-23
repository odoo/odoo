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

    @openerpweb.jsonrequest
    def scan_item_success(self, request):
        """
        A product has been scanned with success
        """
        print 'scan_item_success'
        return 

    @openerpweb.jsonrequest
    def scan_item_error_unrecognized(self, request):
        """
        A product has been scanned without success
        """
        print 'scan_item_error_unrecognized'
        return 

    @openerpweb.jsonrequest
    def help_needed(self, request):
        """
        The user wants an help (ex: light is on)
        """
        print "help_needed"
        return 

    @openerpweb.jsonrequest
    def help_canceled(self, request):
        """
        The user stops the help request
        """
        print "help_canceled"
        return 

    @openerpweb.jsonrequest
    def weighting_start(self, request):
        print "weighting_start"
        return 

    @openerpweb.jsonrequest
    def weighting_read_kg(self, request):
        print "weighting_read_kg"
        return 0.0

    @openerpweb.jsonrequest
    def weighting_end(self, request):
        print "weighting_end"
        return 

    @openerpweb.jsonrequest
    def payment_request(self, request, price, method, info):
        """
        The PoS will activate the method payment 
        """
        print "payment_request: price:"+str(price)+" method:"+str(method)+" info:"+str(info)
        return 

    #@openerpweb.jsonrequest
    def is_payment_accepted(self, request):
        print "is_payment_accepted"
        return 

    #@openerpweb.jsonrequest
    def payment_cancelled(self, request):
        print "payment_cancelled"
        return 

    @openerpweb.jsonrequest
    def transaction_start(self, request):
        print 'transaction_start'
        return 

    @openerpweb.jsonrequest
    def transaction_end(self, request):
        print 'transaction_end'
        return 

    @openerpweb.jsonrequest
    def cashier_mode_activated(self, request):
        print 'cashier_mode_activated'
        return 

    @openerpweb.jsonrequest
    def cashier_mode_deactivated(self, request):
        print 'cashier_mode_deactivated'
        return 

    @openerpweb.jsonrequest
    def open_cashbox(self, request):
        print 'open_cashbox'
        return

    @openerpweb.jsonrequest
    def print_receipt(self, request, receipt):
        print 'print_receipt' + str(receipt)
        return

