odoo.define('pos_reprint.pos_reprint', function (require) {
"use strict";

var devices = require('point_of_sale.devices');
var screens = require('point_of_sale.screens');
var gui = require('point_of_sale.gui');
var core = require('web.core');

var _t = core._t;
var QWeb = core.qweb;

devices.ProxyDevice.include({
    print_receipt: function(receipt) { 
        this._super(receipt);
        this.pos.old_receipt = receipt || this.pos.old_receipt;
    },
});

screens.ReceiptScreenWidget.include({
    show_receipt: function(receipt) {
        this._super(receipt);
        this.pos.old_receipt_html = receipt || this.pos.old_receipt_html;
    },
})
/*--------------------------------------*\
 |         THE RECEIPT REPRINT SCREEN           |
\*======================================*/

// The receipt screen displays the order's
// receipt and allows it to be printed in a web browser.
// The receipt screen is not shown if the point of sale
// is set up to print with the proxy. Altough it could
// be useful to do so...

var ReceiptReprintScreenWidget = screens.ScreenWidget.extend({
    template: 'ReceiptScreenWidget',
    show: function(){
        this._super();
        var self = this;
        this.$('.next').text('Fortsetzen');
        this.$('.change-value').parent('h1').hide();
        this.render_receipt();
        this.handle_auto_print();
    },
    handle_auto_print: function() {
        if (this.should_auto_print()) {
            this.print();
            if (this.should_close_immediately()){
                this.click_back();
            }
        } else {
            this.lock_screen(false);
        }
    },
    should_auto_print: function() {
        return this.pos.config.iface_print_auto;
    },
    should_close_immediately: function() {
        return this.pos.config.iface_print_via_proxy && this.pos.config.iface_print_skip_screen;
    },
    lock_screen: function(locked) {
        this._locked = locked;
        if (locked) {
            this.$('.next').removeClass('highlight');
        } else {
            this.$('.next').addClass('highlight');
        }
    },
    print_web: function() {
        window.print();
    },
    print_xml: function() {
        this.pos.proxy.print_receipt(this.pos.old_receipt);
    },
    print: function() {
        var self = this;

        if (!this.pos.config.iface_print_via_proxy) { // browser (html) printing

            // The problem is that in chrome the print() is asynchronous and doesn't
            // execute until all rpc are finished. So it conflicts with the rpc used
            // to send the orders to the backend, and the user is able to go to the next 
            // screen before the printing dialog is opened. The problem is that what's 
            // printed is whatever is in the page when the dialog is opened and not when it's called,
            // and so you end up printing the product list instead of the receipt... 
            //
            // Fixing this would need a re-architecturing
            // of the code to postpone sending of orders after printing.
            //
            // But since the print dialog also blocks the other asynchronous calls, the
            // button enabling in the setTimeout() is blocked until the printing dialog is 
            // closed. But the timeout has to be big enough or else it doesn't work
            // 1 seconds is the same as the default timeout for sending orders and so the dialog
            // should have appeared before the timeout... so yeah that's not ultra reliable. 

            this.lock_screen(true);

            setTimeout(function(){
                self.lock_screen(false);
            }, 1000);

            this.print_web();
        } else {    // proxy (xml) printing
            this.print_xml();
            this.lock_screen(false);
        }
    },
    click_next: function() {
        this.pos.gui.show_screen('products');
    },
    click_back: function() {
        // Placeholder method for ReceiptScreen extensions that
        // can go back ...
    },
    renderElement: function() {
        var self = this;
        this._super();
        this.$('.next').click(function(){
            if (!self._locked) {
                self.click_next();
            }
        });
        this.$('.back').click(function(){
            if (!self._locked) {
                self.click_back();
            }
        });
        this.$('.button.print').click(function(){
            if (!self._locked) {
                self.print();
            }
        });
    },
    render_receipt: function() {
        this.$('.pos-receipt-container').html(this.pos.old_receipt_html);
    },
});
gui.define_screen({name:'receipt_reprint', widget: ReceiptReprintScreenWidget});

var ReprintButton = screens.ActionButtonWidget.extend({
    template: 'ReprintButton',
    button_click: function() {
        if (this.pos.old_receipt_html) {
            this.pos.gui.show_screen('receipt_reprint');
        } else {
            this.gui.show_popup('error', {
                'title': _t('Nothing to Print'),
                'body':  _t('There is no previous receipt to print.'),
            });
        }
    },
});

screens.define_action_button({
    'name': 'reprint',
    'widget': ReprintButton,
    'condition': function(){
        return this.pos.config.iface_reprint;
    },
});

return {
    ReceiptReprintScreenWidget: ReceiptReprintScreenWidget,
};

});
