# -*- coding: utf-8 -*-
import logging
import simplejson

try:
    import openerp.addons.web.common.http as openerpweb
    from openerp.addons.web.controllers.main import manifest_list, module_boot, html_template
except ImportError:
    import web.common.http as openerpweb

class PointOfSaleController(openerpweb.Controller):
    _cp_path = '/pos'

    @openerpweb.httprequest
    def app(self, req, s_action=None, **kw):
        js = "\n        ".join('<script type="text/javascript" src="%s"></script>' % i for i in manifest_list(req, None, 'js'))
        css = "\n        ".join('<link rel="stylesheet" href="%s">' % i for i in manifest_list(req, None, 'css'))

        cookie = req.httprequest.cookies.get("instance0|session_id")
        session_id = cookie.replace("%22","")
        template = html_template.replace('<html','<html manifest="/pos/manifest?session_id=%s"'%session_id)
        r = template % {
            'js': js,
            'css': css,
            'modules': simplejson.dumps(module_boot(req)),
            'init': 'var wc = new s.web.WebClient();wc.appendTo($(document.body));'
        }
        return r

    @openerpweb.httprequest
    def manifest(self, req, **kwargs):
        ml = ["CACHE MANIFEST"]
        Products = req.session.model('product.product')
        for p in Products.search_read([('pos_categ_id','!=',False)], ['name', 'dependencies_id']):
            session_id = req.session_id
            product_id = p['id']
            url = "/web/binary/image?session_id=%s&model=product.product&field=image&id=%s" % (session_id, product_id)
            ml.append(url)
        ml += ["NETWORK:","*"]
        m = "\n".join(ml)
        return m

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

    @openerpweb.jsonrequest
    def is_payment_accepted(self, request):
        print "is_payment_accepted"
        return 'waiting_for_payment' 

    @openerpweb.jsonrequest
    def payment_canceled(self, request):
        print "payment_canceled"
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


