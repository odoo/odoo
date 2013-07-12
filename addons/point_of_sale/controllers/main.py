# -*- coding: utf-8 -*-
import logging
import simplejson
import os
import openerp

from openerp.addons.web import http
from openerp.addons.web.http import request
from openerp.addons.web.controllers.main import manifest_list, module_boot, html_template

class PointOfSaleController(http.Controller):

    @http.route('/pos/app', type='http', auth='admin')
    def app(self):
        js = "\n        ".join('<script type="text/javascript" src="%s"></script>' % i for i in manifest_list('js',db=request.db))
        css = "\n        ".join('<link rel="stylesheet" href="%s">' % i for i in manifest_list('css',db=request.db))

        cookie = request.httprequest.cookies.get("instance0|session_id")
        session_id = cookie.replace("%22","")
        template = html_template.replace('<html','<html manifest="/pos/manifest?session_id=%s"' % request.session_id)

        r = template % {
            'js': js,
            'css': css,
            'modules': simplejson.dumps(module_boot(request)),
            'init': 'var wc = new s.web.WebClient();wc.appendTo($(document.body));'
        }
        return r

    @http.route('/pos/manifest',type='http', auth='admin')
    def manifest(self):
        """ This generates a HTML5 cache manifest files that preloads the categories and products thumbnails 
            and other ressources necessary for the point of sale to work offline """

        ml = ["CACHE MANIFEST"]

        # loading all the images in the static/src/img/* directories
        def load_css_img(srcdir,dstdir):
            for f in os.listdir(srcdir):
                path = os.path.join(srcdir,f)
                dstpath = os.path.join(dstdir,f)
                if os.path.isdir(path) :
                    load_css_img(path,dstpath)
                elif f.endswith(('.png','.PNG','.jpg','.JPG','.jpeg','.JPEG','.gif','.GIF')):
                    ml.append(dstpath)

        imgdir = openerp.modules.get_module_resource('point_of_sale','static/src/img');
        load_css_img(imgdir,'/point_of_sale/static/src/img')
        
        products = request.registry.get('product.product')
        for p in products.search_read(request.cr, request.uid, [('pos_categ_id','!=',False)], ['name']):
            product_id = p['id']
            url = "/web/binary/image?session_id=%s&model=product.product&field=image&id=%s" % (request.session_id, product_id)
            ml.append(url)
        
        categories = request.registry.get('pos.category')
        for c in categories.search_read(request.cr, request.uid, [], ['name']):
            category_id = c['id']
            url = "/web/binary/image?session_id=%s&model=pos.category&field=image&id=%s" % (request.session_id, category_id)
            ml.append(url)

        ml += ["NETWORK:","*"]
        m = "\n".join(ml)

        return m

    @http.route('/pos/scan_item_success', type='json', auth='admin')
    def scan_item_success(self, ean):
        """
        A product has been scanned with success
        """
        print 'scan_item_success: ' + str(ean)
        return 

    @http.route('/pos/scan_item_error_unrecognized')
    def scan_item_error_unrecognized(self, ean):
        """
        A product has been scanned without success
        """
        print 'scan_item_error_unrecognized: ' + str(ean)
        return 

    @http.route('/pos/help_needed', type='json', auth='admin')
    def help_needed(self):
        """
        The user wants an help (ex: light is on)
        """
        print "help_needed"
        return 

    @http.route('/pos/help_canceled', type='json', auth='admin')
    def help_canceled(self):
        """
        The user stops the help request
        """
        print "help_canceled"
        return 

    @http.route('/pos/weighting_start', type='json', auth='admin')
    def weighting_start(self):
        print "weighting_start"
        return 

    @http.route('/pos/weighting_read_kg', type='json', auth='admin')
    def weighting_read_kg(self):
        print "weighting_read_kg"
        return 3.14

    @http.route('/pos/weighting_end', type='json', auth='admin')
    def weighting_end(self):
        print "weighting_end"
        return 

    @http.route('/pos/payment_request', type='json', auth='admin')
    def payment_request(self, price):
        """
        The PoS will activate the method payment 
        """
        print "payment_request: price:"+str(price)
        return 'ok'

    @http.route('/pos/payment_status', type='json', auth='admin')
    def payment_status(self):
        print "payment_status"
        return { 'status':'waiting' } 

    @http.route('/pos/payment_cancel', type='json', auth='admin')
    def payment_cancel(self):
        print "payment_cancel"
        return 

    @http.route('/pos/transaction_start', type='json', auth='admin')
    def transaction_start(self):
        print 'transaction_start'
        return 

    @http.route('/pos/transaction_end', type='json', auth='admin')
    def transaction_end(self):
        print 'transaction_end'
        return 

    @http.route('/pos/cashier_mode_activated', type='json', auth='admin')
    def cashier_mode_activated(self):
        print 'cashier_mode_activated'
        return 

    @http.route('/pos/cashier_mode_deactivated', type='json', auth='admin')
    def cashier_mode_deactivated(self):
        print 'cashier_mode_deactivated'
        return 

    @http.route('/pos/open_cashbox', type='json', auth='admin')
    def open_cashbox(self):
        print 'open_cashbox'
        return

    @http.route('/pos/print_receipt', type='json', auth='admin')
    def print_receipt(self, receipt):
        print 'print_receipt' + str(receipt)
        return

    @http.route('/pos/print_pdf_invoice', type='json', auth='admin')
    def print_pdf_invoice(self, pdfinvoice):
        print 'print_pdf_invoice' + str(pdfinvoice)
        return


