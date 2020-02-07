odoo.define('point_of_sale.screens', function (require) {
"use strict";
// This file contains the Screens definitions. Screens are the
// content of the right pane of the pos, containing the main functionalities. 
//
// Screens must be defined and named in chrome.js before use.
//
// Screens transitions are controlled by the Gui.
//  gui.set_startup_screen() sets the screen displayed at startup
//  gui.set_default_screen() sets the screen displayed for new orders
//  gui.show_screen() shows a screen
//  gui.back() goes to the previous screen
//
// Screen state is saved in the order. When a new order is selected,
// a screen is displayed based on the state previously saved in the order.
// this is also done in the Gui with:
//  gui.show_saved_screen()
//
// All screens inherit from ScreenWidget. The only addition from the base widgets
// are show() and hide() which shows and hides the screen but are also used to 
// bind and unbind actions on widgets and devices. The gui guarantees
// that only one screen is shown at the same time and that show() is called after all
// hide()s
//
// Each Screens must be independant from each other, and should have no 
// persistent state outside the models. Screen state variables are reset at
// each screen display. A screen can be called with parameters, which are
// to be used for the duration of the screen only. 

var PosBaseWidget = require('point_of_sale.BaseWidget');
var gui = require('point_of_sale.gui');
var core = require('web.core');
var rpc = require('web.rpc');
var utils = require('web.utils');
var field_utils = require('web.field_utils');
var BarcodeEvents = require('barcodes.BarcodeEvents').BarcodeEvents;
var Printer = require('point_of_sale.Printer').Printer;

const { OrderWidget } = require('point_of_sale.OrderWidget');
const { NumpadWidget } = require('point_of_sale.NumpadWidget');
const { ActionpadWidget } = require('point_of_sale.ActionpadWidget');
const { ProductsWidget } = require('point_of_sale.ProductsWidget');

var QWeb = core.qweb;
var _t = core._t;

var round_pr = utils.round_precision;

/*--------------------------------------*\
 |          THE SCREEN WIDGET           |
\*======================================*/

// The screen widget is the base class inherited
// by all screens.
var ScreenWidget = PosBaseWidget.extend({

    init: function(parent,options){
        this._super(parent,options);
        this.hidden = false;
    },

    barcode_product_screen:         'products',     //if defined, this screen will be loaded when a product is scanned

    // what happens when a product is scanned : 
    // it will add the product to the order and go to barcode_product_screen. 
    barcode_product_action: function(code){
        var self = this;
        if (self.pos.scan_product(code)) {
            if (self.barcode_product_screen) {
                self.gui.show_screen(self.barcode_product_screen, null, null, true);
            }
        } else {
            this.barcode_error_action(code);
        }
    },
    
    // what happens when a client id barcode is scanned.
    // the default behavior is the following : 
    // - if there's a user with a matching barcode, put it as the active 'client' and return true
    // - else : return false. 
    barcode_client_action: function(code){
        var partner = this.pos.db.get_partner_by_barcode(code.code);
        if(partner){
            if (this.pos.get_order().get_client() !== partner) {
                this.pos.get_order().set_client(partner);
                this.pos.get_order().set_pricelist(_.findWhere(this.pos.pricelists, {'id': partner.property_product_pricelist[0]}) || this.pos.default_pricelist);
            }
            return true;
        }
        this.barcode_error_action(code);
        return false;
    },
    
    // what happens when a discount barcode is scanned : the default behavior
    // is to set the discount on the last order.
    barcode_discount_action: function(code){
        var last_orderline = this.pos.get_order().get_last_orderline();
        if(last_orderline){
            last_orderline.set_discount(code.value);
        }
    },
    // What happens when an invalid barcode is scanned : shows an error popup.
    barcode_error_action: function(code) {
        var show_code;
        if (code.code.length > 32) {
            show_code = code.code.substring(0,29)+'...';
        } else {
            show_code = code.code;
        }
        this.gui.show_popup('error-barcode',show_code);
    },

    // this method shows the screen and sets up all the widget related to this screen. Extend this method
    // if you want to alter the behavior of the screen.
    show: function(){
        var self = this;

        this.hidden = false;
        if(this.$el){
            this.$el.removeClass('oe_hidden');
        }

        this.pos.barcode_reader.set_action_callback({
            'product': _.bind(self.barcode_product_action, self),
            'weight': _.bind(self.barcode_product_action, self),
            'price': _.bind(self.barcode_product_action, self),
            'client' : _.bind(self.barcode_client_action, self),
            'discount': _.bind(self.barcode_discount_action, self),
            'error'   : _.bind(self.barcode_error_action, self),
        });
    },

    // this method is called when the screen is closed to make place for a new screen. this is a good place
    // to put your cleanup stuff as it is guaranteed that for each show() there is one and only one close()
    close: function(){
        if(this.pos.barcode_reader){
            this.pos.barcode_reader.reset_action_callbacks();
        }

        if(this.payment_interface){
            this.payment_interface.close();
        }
    },

    // this methods hides the screen. It's not a good place to put your cleanup stuff as it is called on the
    // POS initialization.
    hide: function(){
        this.hidden = true;
        if(this.$el){
            this.$el.addClass('oe_hidden');
        }
    },

    // we need this because some screens re-render themselves when they are hidden
    // (due to some events, or magic, or both...)  we must make sure they remain hidden.
    // the good solution would probably be to make them not re-render themselves when they
    // are hidden. 
    renderElement: function(){
        this._super();
        if(this.hidden){
            if(this.$el){
                this.$el.addClass('oe_hidden');
            }
        }
    },
    /**
     * Handles the error response from the server when we push
     * an invoiceable order
     * Displays appropriates warnings and errors and
     * proposes subsequent actions
     *
     * @private
     * @param {PosModel} order: the order to consider, defaults to current order
     * @param {Boolean} refresh_screens: whether or not displayed screens should refresh
     * @param {Object} error: the error provided by Ajax
     */
    _handleFailedPushOrder: function (order, refresh_screen, error) {
        var self = this;
        order = order || this.pos.get_order();
        this.invoicing = false;
        order.finalized = false;
        if (error.message === 'Missing Customer') {
            this.gui.show_popup('confirm',{
                'title': _t('Please select the Customer'),
                'body': _t('You need to select the customer before you can invoice an order.'),
                confirm: function(){
                    self.gui.show_screen('clientlist', null, refresh_screen);
                },
            });
        } else if (error.message === 'Backend Invoice') {
            this.gui.show_popup('confirm',{
                'title': _t('Please print the invoice from the backend'),
                'body': _t('The order has been synchronized earlier. Please make the invoice from the backend for the order: ') + error.data.order.name,
                confirm: function () {
                    this.gui.show_screen('receipt', null, refresh_screen);
                },
                cancel: function () {
                    this.gui.show_screen('receipt', null, refresh_screen);
                },
            });
        } else if (error.code < 0) {        // XmlHttpRequest Errors
            this.gui.show_popup('error',{
                'title': _t('The order could not be sent'),
                'body': _t('Check your internet connection and try again.'),
                cancel: function () {
                    this.gui.show_screen('receipt', {button_print_invoice: true}, refresh_screen); // refresh if necessary
                },
            });
        } else if (error.code === 200) {    // OpenERP Server Errors
            this.gui.show_popup('error-traceback',{
                'title': error.data.message || _t("Server Error"),
                'body': error.data.debug || _t('The server encountered an error while receiving your order.'),
            });
        } else {                            // ???
            this.gui.show_popup('error',{
                'title': _t("Unknown Error"),
                'body':  _t("The order could not be sent to the server due to an unknown error"),
            });
        }
    },
});


/*--------------------------------------*\
 |          THE SCALE SCREEN            |
\*======================================*/

// The scale screen displays the weight of
// a product on the electronic scale.

var ScaleScreenWidget = ScreenWidget.extend({
    template:'ScaleScreenWidget',

    next_screen: 'products',
    previous_screen: 'products',

    show: function(){
        this._super();
        var self = this;

        this.set_weight(0);
        this.renderElement();

        this.hotkey_handler = function(event){
            if(event.which === 13){
                self.order_product();
                self.gui.show_screen(self.next_screen);
            }else if(event.which === 27){
                self.gui.show_screen(self.previous_screen);
            }
        };

        $('body').on('keypress',this.hotkey_handler);

        this.$('.back').click(function(){
            self.gui.show_screen(self.previous_screen);
        });

        this.$('.next,.buy-product').click(function(){
            self.gui.show_screen(self.next_screen);
            // add product *after* switching screen to scroll properly
            self.order_product();
        });
        this._read_scale();
    },

    _read_scale: function() {
        var self = this;
        var queue = this.pos.proxy_queue;
        queue.schedule(function(){
            return self.pos.proxy.scale_read().then(function(weight){
                self.set_weight(weight.weight);
            });
        },{duration:500, repeat: true});

    },
    get_product: function(){
        return this.gui.get_current_screen_param('product');
    },
    _get_active_pricelist: function(){
        var current_order = this.pos.get_order();
        var current_pricelist = this.pos.default_pricelist;

        if (current_order) {
            current_pricelist = current_order.pricelist;
        }

        return current_pricelist;
    },
    order_product: function(){
        this.pos.get_order().add_product(this.get_product(),{ quantity: this.weight });
    },
    get_product_name: function(){
        var product = this.get_product();
        return (product ? product.display_name : undefined) || 'Unnamed Product';
    },
    get_product_price: function(){
        var product = this.get_product();
        var pricelist = this._get_active_pricelist();
        return (product ? product.get_price(pricelist, this.weight) : 0) || 0;
    },
    get_product_uom: function(){
        var product = this.get_product();

        if(product){
            return this.pos.units_by_id[product.uom_id[0]].name;
        }else{
            return '';
        }
    },
    set_weight: function(weight){
        this.weight = weight;
        this.$('.weight').text(this.get_product_weight_string());
        this.$('.computed-price').text(this.get_computed_price_string());
    },
    get_product_weight_string: function(){
        var product = this.get_product();
        var defaultstr = (this.weight || 0).toFixed(3) + ' Kg';
        if(!product || !this.pos){
            return defaultstr;
        }
        var unit_id = product.uom_id;
        if(!unit_id){
            return defaultstr;
        }
        var unit = this.pos.units_by_id[unit_id[0]];
        var weight = round_pr(this.weight || 0, unit.rounding);
        var weightstr = weight.toFixed(Math.ceil(Math.log(1.0/unit.rounding) / Math.log(10) ));
        weightstr += ' ' + unit.name;
        return weightstr;
    },
    get_computed_price_string: function(){
        return this.format_currency(this.get_product_price() * this.weight);
    },
    close: function(){
        this._super();
        $('body').off('keypress',this.hotkey_handler);

        this.pos.proxy_queue.clear();
    },
});
gui.define_screen({name: 'scale', widget: ScaleScreenWidget});

/*--------------------------------------*\
 |         THE PRODUCT SCREEN           |
\*======================================*/

// The product screen contains the list of products,
// The category selector and the order display.
// It is the default screen for orders and the
// startup screen for shops.
//
// There product screens uses many sub-widgets,
// the code follows.


/* -------- The Action Buttons -------- */

// Above the numpad and the actionpad, buttons
// for extra actions and controls by point of
// sale extensions modules. 

var action_button_classes = [];
var define_action_button = function(classe, options){
    options = options || {};

    var classes = action_button_classes;
    var index   = classes.length;
    var i;

    if (options.after) {
        for (i = 0; i < classes.length; i++) {
            if (classes[i].name === options.after) {
                index = i + 1;
            }
        }
    } else if (options.before) {
        for (i = 0; i < classes.length; i++) {
            if (classes[i].name === options.after) {
                index = i;
                break;
            }
        }
    }
    classes.splice(i,0,classe);
};

var ActionButtonWidget = PosBaseWidget.extend({
    template: 'ActionButtonWidget',
    label: _t('Button'),
    renderElement: function(){
        var self = this;
        this._super();
        this.$el.click(function(){
            self.button_click();
        });
    },
    button_click: function(){},
    highlight: function(highlight){
        this.$el.toggleClass('highlight',!!highlight);
    },
    // alternative highlight color
    altlight: function(altlight){
        this.$el.toggleClass('altlight',!!altlight);
    },
});

/* -------- The Product Screen -------- */

var ProductScreenWidget = ScreenWidget.extend({
    template:'ProductScreenWidget',

    init: function() {
        this._super.apply(this, arguments);
        this.timeout = null;
        this.buffered_key_events = [];
    },

    start: function(){ 

        this.actionpad = new ActionpadWidget(null, { pos: this.pos, gui: this.gui });
        this.actionpad.mount(this.$('.placeholder-ActionpadWidget')[0], {position: "self"});

        this.numpad = new NumpadWidget(null, { pos: this.pos });
        this.numpad.mount(this.$('.placeholder-NumpadWidget')[0], {position: "self"});

        this.orderWidget = new OrderWidget(null, {
            order: this.pos.get_order(),
            pos: this.pos,
            numpadState: this.numpad.state,
        });
        this.orderWidget.mount(this.$('.placeholder-OrderWidget')[0], {position: "self"});

        this.pos.on('change:selectedOrder', () => {
            this.orderWidget.unmount();
            this.orderWidget = new OrderWidget(null, {
                pos: this.pos,
                order: this.pos.get_order(),
                numpadState: this.numpad.state,
            });
            this.orderWidget.mount(this.$('.placeholder-OrderWidget')[0], {position: "self"})
        })

        this.productsWidget = new ProductsWidget(null, {
            pos: this.pos,
            clickProductHandler: product => this.click_product(product),
        });
        this.productsWidget.mount(this.$('.placeholder-ProductsWidget')[0], {position: "self"});

        this.action_buttons = {};
        var classes = action_button_classes;
        for (var i = 0; i < classes.length; i++) {
            var classe = classes[i];
            if ( !classe.condition || classe.condition.call(this) ) {
                var widget = new classe.widget(this,{});
                widget.appendTo(this.$('.control-buttons'));
                this.action_buttons[classe.name] = widget;
            }
        }
        if (_.size(this.action_buttons)) {
            this.$('.control-buttons').removeClass('oe_hidden');
        }
        this._onKeypadKeyDown = this._onKeypadKeyDown.bind(this);
    },

    click_product: function(product) {
       if(product.to_weight && this.pos.config.iface_electronic_scale){
           this.gui.show_screen('scale',{product: product});
       }else{
           this.pos.get_order().add_product(product);
       }
    },

    show: function(reset){
        this._super();
        if (reset) {
            this.numpad.state.reset();
        }
        if (this.pos.config.iface_vkeyboard && this.chrome.widget.keyboard) {
            this.chrome.widget.keyboard.connect($(this.el.querySelector('.searchbox input')));
        }
        $(document).on('keydown.productscreen', this._onKeypadKeyDown);
    },
    close: function(){
        this._super();
        if(this.pos.config.iface_vkeyboard && this.chrome.widget.keyboard){
            this.chrome.widget.keyboard.hide();
        }
        $(document).off('keydown.productscreen', this._onKeypadKeyDown);
    },

    /**
     * Buffers the key typed and distinguishes between actual keystrokes and
     * scanner inputs.
     *
     * @private
     * @param {event} ev - The keyboard event.
    */
    _onKeypadKeyDown: function (ev) {
        //prevent input and textarea keydown event
        if(!_.contains(["INPUT", "TEXTAREA"], $(ev.target).prop('tagName'))) {
            clearTimeout(this.timeout);
            this.buffered_key_events.push(ev);
            this.timeout = setTimeout(_.bind(this._handleBufferedKeys, this), BarcodeEvents.max_time_between_keys_in_ms);
        }
    },

    /**
     * Processes the buffer of keys filled by _onKeypadKeyDown and
     * distinguishes between the actual keystrokes and scanner inputs.
     *
     * @private
    */
    _handleBufferedKeys: function () {
        // If more than 2 keys are recorded in the buffer, chances are high that the input comes
        // from a barcode scanner. In this case, we don't do anything.
        if (this.buffered_key_events.length > 2) {
            this.buffered_key_events = [];
            return;
        }

        for (var i = 0; i < this.buffered_key_events.length; ++i) {
            var ev = this.buffered_key_events[i];
            if ((ev.key >= "0" && ev.key <= "9") || ev.key === ".") {
               this.numpad.state.appendNewChar(ev.key);
            }
            else {
                switch (ev.key){
                    case "Backspace":
                        this.numpad.state.deleteLastChar();
                        break;
                    case "Delete":
                        this.numpad.state.resetValue();
                        break;
                    case ",":
                        this.numpad.state.appendNewChar(".");
                        break;
                    case "+":
                        this.numpad.state.positiveSign();
                        break;
                    case "-":
                        this.numpad.state.negativeSign();
                        break;
                }
            }
        }
        this.buffered_key_events = [];
    },
});
gui.define_screen({name:'products', widget: ProductScreenWidget});



/*--------------------------------------*\
 |         THE PAYMENT SCREEN           |
\*======================================*/

// The Payment Screen handles the payments, and
// it is unfortunately quite complicated.

var PaymentScreenWidget = ScreenWidget.extend({
    template:      'PaymentScreenWidget',
    back_screen:   'product',
    init: function(parent, options) {
        var self = this;
        this._super(parent, options);

        this.pos.on('change:selectedOrder',function(){
                this.renderElement();
                this.watch_order_changes();
            },this);
        this.watch_order_changes();

        this.inputbuffer = "";
        this.firstinput  = true;
        this.decimal_point = _t.database.parameters.decimal_point;
        
        // This is a keydown handler that prevents backspace from
        // doing a back navigation. It also makes sure that keys that
        // do not generate a keypress in Chrom{e,ium} (eg. delete,
        // backspace, ...) get passed to the keypress handler.
        this.keyboard_keydown_handler = function(event){
            if (event.keyCode === 8 || event.keyCode === 46) { // Backspace and Delete
                event.preventDefault();

                // These do not generate keypress events in
                // Chrom{e,ium}. Even if they did, we just called
                // preventDefault which will cancel any keypress that
                // would normally follow. So we call keyboard_handler
                // explicitly with this keydown event.
                self.keyboard_handler(event);
            }
        };
        
        // This keyboard handler listens for keypress events. It is
        // also called explicitly to handle some keydown events that
        // do not generate keypress events.
        this.keyboard_handler = function(event){
            // On mobile Chrome BarcodeEvents relies on an invisible
            // input being filled by a barcode device. Let events go
            // through when this input is focused.
            if (BarcodeEvents.$barcodeInput && BarcodeEvents.$barcodeInput.is(":focus")) {
                return;
            }

            var key = '';

            if (event.type === "keypress") {
                if (event.keyCode === 13) { // Enter
                    self.validate_order();
                } else if ( event.keyCode === 190 || // Dot
                            event.keyCode === 110 ||  // Decimal point (numpad)
                            event.keyCode === 188 ||  // Comma
                            event.keyCode === 46 ) {  // Numpad dot
                    key = self.decimal_point;
                } else if (event.keyCode >= 48 && event.keyCode <= 57) { // Numbers
                    key = '' + (event.keyCode - 48);
                } else if (event.keyCode === 45) { // Minus
                    key = '-';
                } else if (event.keyCode === 43) { // Plus
                    key = '+';
                }
            } else { // keyup/keydown
                if (event.keyCode === 46) { // Delete
                    key = 'CLEAR';
                } else if (event.keyCode === 8) { // Backspace
                    key = 'BACKSPACE';
                }
            }

            self.payment_input(key);
            event.preventDefault();
        };

        this.pos.on('change:selectedClient', function() {
            self.customer_changed();
        }, this);
    },
    // resets the current input buffer
    reset_input: function(){
        var line = this.pos.get_order().selected_paymentline;
        this.firstinput  = true;
        if (line) {
            this.inputbuffer = this.format_currency_no_symbol(line.get_amount());
        } else {
            this.inputbuffer = "";
        }
    },
    // handle both keyboard and numpad input. Accepts
    // a string that represents the key pressed.
    payment_input: function(input) {
        var paymentline = this.pos.get_order().selected_paymentline;

        // disable changing amount on paymentlines with running or done payments on a payment terminal
        if (this.payment_interface && !['pending', 'retry'].includes(paymentline.get_payment_status())) {
            return;
        }

        var newbuf = this.gui.numpad_input(this.inputbuffer, input, {'firstinput': this.firstinput});

        this.firstinput = (newbuf.length === 0);

        // popup block inputs to prevent sneak editing. 
        if (this.gui.has_popup()) {
            return;
        }
        
        if (newbuf !== this.inputbuffer) {
            this.inputbuffer = newbuf;
            var order = this.pos.get_order();
            if (paymentline) {
                var amount = this.inputbuffer;

                if (this.inputbuffer !== "-") {
                    amount = field_utils.parse.float(this.inputbuffer);
                }

                paymentline.set_amount(amount);
                this.render_paymentlines();
                this.$('.paymentline.selected .edit').text(this.format_currency_no_symbol(amount));
            }
        }
    },
    click_numpad: function(button) {
	var paymentlines = this.pos.get_order().get_paymentlines();
	var open_paymentline = false;

    // if one of the paymentlines is not paid,
    // then do not make a new line.
    // if everything is paid, then make a new line.
	for (var i = 0; i < paymentlines.length; i++) {
	    if (! paymentlines[i].paid) {
		open_paymentline = true;
	    }
	}

	if (! open_paymentline) {
            this.pos.get_order().add_paymentline( this.pos.payment_methods[0]);
            this.render_paymentlines();
        }

        this.payment_input(button.data('action'));
    },
    render_numpad: function() {
        var self = this;
        var numpad = $(QWeb.render('PaymentScreen-Numpad', { widget:this }));
        numpad.on('click','button',function(){
            self.click_numpad($(this));
        });
        return numpad;
    },
    click_delete_paymentline: function(cid){
        var lines = this.pos.get_order().get_paymentlines();
        for ( var i = 0; i < lines.length; i++ ) {
            var line = lines[i];
            if (line.cid === cid) {
                // If a paymentline with a payment terminal linked to
                // it is removed, the terminal should get a cancel
                // request.
                if (['waiting', 'waitingCard', 'timeout'].includes(lines[i].get_payment_status())) {
                    line.payment_method.payment_terminal.send_payment_cancel(this.pos.get_order(), cid);
                }

                this.pos.get_order().remove_paymentline(line);
                this.reset_input();
                this.render_paymentlines();
                return;
            }
        }
    },
    click_paymentline: function(cid){
        var lines = this.pos.get_order().get_paymentlines();
        for ( var i = 0; i < lines.length; i++ ) {
            if (lines[i].cid === cid) {
                this.pos.get_order().select_paymentline(lines[i]);
                this.reset_input();
                this.render_paymentlines();
                return;
            }
        }
    },
    /**
     * link the proper functions to buttons for payment terminals
     * send_payment_request, force_payment_done and cancel_payment.
     */
    render_payment_terminal: function() {
        var self = this;
        var order = this.pos.get_order();
        if (!order) {
            return;
        }

        this.$el.find('.send_payment_request').click(function () {
            var cid = $(this).data('cid');
            // Other payment lines can not be reversed anymore
            order.get_paymentlines().forEach(function (line) {
                line.can_be_reversed = false;
            });

            var line = self.pos.get_order().get_paymentline(cid);
            var payment_terminal = line.payment_method.payment_terminal;
            line.set_payment_status('waiting');
            self.render_paymentlines();

            payment_terminal.send_payment_request(cid).then(function (payment_successful) {
                if (payment_successful) {
                    line.set_payment_status('done');
                    line.can_be_reversed = self.payment_interface.supports_reversals;
                    self.reset_input(); // in case somebody entered a tip the amount tendered should be updated
                } else {
                    line.set_payment_status('retry');
                }
            }).finally(function () {
                self.render_paymentlines();
            });

            self.render_paymentlines();
        });
        this.$el.find('.send_payment_cancel').click(function () {
            var cid = $(this).data('cid');
            var line = self.pos.get_order().get_paymentline($(this).data('cid'));
            var payment_terminal = line.payment_method.payment_terminal;
            line.set_payment_status('waitingCancel');
            self.render_paymentlines();

            payment_terminal.send_payment_cancel(self.pos.get_order(), cid).finally(function () {
                line.set_payment_status('retry');
                self.render_paymentlines();
            });

            self.render_paymentlines();
        });
        this.$el.find('.send_payment_reversal').click(function () {
            var cid = $(this).data('cid');
            var line = self.pos.get_order().get_paymentline($(this).data('cid'));
            var payment_terminal = line.payment_method.payment_terminal;
            line.set_payment_status('reversing');
            self.render_paymentlines();

            payment_terminal.send_payment_reversal(cid).then(function (reversal_successful) {
                if (reversal_successful) {
                    line.set_amount(0);
                    line.set_payment_status('reversed');
                } else {
                    line.can_be_reversed = false;
                    line.set_payment_status('done');
                }
                self.render_paymentlines();
            });
        });

        this.$el.find('.send_force_done').click(function () {
            var line = self.pos.get_order().get_paymentline($(this).data('cid'));
            var payment_terminal = line.payment_method.payment_terminal;
            line.set_payment_status('done');
            self.render_paymentlines();
        });
    },
    render_paymentlines: function() {
        var self  = this;
        var order = this.pos.get_order();
        if (!order) {
            return;
        }

        var lines = order.get_paymentlines();
        var extradue = this.compute_extradue(order);

        this.$('.paymentlines-container').empty();
        var lines = $(QWeb.render('PaymentScreen-Paymentlines', {
            widget: this, 
            order: order,
            paymentlines: lines,
            extradue: extradue,
        }));

        lines.on('click','.delete-button',function(){
            self.click_delete_paymentline($(this).data('cid'));
        });

        lines.on('click','.paymentline',function(){
            self.click_paymentline($(this).data('cid'));
        });
            
        lines.appendTo(this.$('.paymentlines-container'));

        this.render_payment_terminal();
    },
    compute_extradue: function (order) {
        var lines = order.get_paymentlines();
        var due   = order.get_due();
        if (due && lines.length && (due !== order.get_due(lines[lines.length-1]) || lines[lines.length - 1].payment_status === 'reversed')) {
            return due;
        }
        return 0;
    },
    click_paymentmethods: function(id) {
        var payment_method = this.pos.payment_methods_by_id[id];
        var order = this.pos.get_order();

        if (order.electronic_payment_in_progress()) {
            this.gui.show_popup('error',{
                'title': _t('Error'),
                'body':  _t('There is already an electronic payment in progress.'),
            });
            return false;
        } else {
            order.add_paymentline(payment_method);
            this.reset_input();

            this.payment_interface = payment_method.payment_terminal;
            if (this.payment_interface) {
                order.selected_paymentline.set_payment_status('pending');
            }

            this.render_paymentlines();
        }
        return true;
    },
    render_paymentmethods: function() {
        var self = this;
        var methods = $(QWeb.render('PaymentScreen-Paymentmethods', { widget:this }));
            methods.on('click','.paymentmethod',function(){
                self.click_paymentmethods($(this).data('id'));
            });
        return methods;
    },
    click_invoice: function(){
        var order = this.pos.get_order();
        order.set_to_invoice(!order.is_to_invoice());
        if (order.is_to_invoice()) {
            this.$('.js_invoice').addClass('highlight');
        } else {
            this.$('.js_invoice').removeClass('highlight');
        }
    },
    click_email: function(){
        var order = this.pos.get_order();
        order.set_to_email(!order.is_to_email());
        this.$('.js_email').toggleClass('highlight', order.is_to_email());
    },
    click_tip: function(){
        var self   = this;
        var order  = this.pos.get_order();
        var tip    = order.get_tip();
        var change = order.get_change();
        var value  = tip;

        if (tip === 0 && change > 0  ) {
            value = change;
        }

        this.gui.show_popup('number',{
            'title': tip ? _t('Change Tip') : _t('Add Tip'),
            'value': self.format_currency_no_symbol(value),
            'confirm': function(value) {
                order.set_tip(field_utils.parse.float(value));
                self.render_paymentlines();
            }
        });
    },
    customer_changed: function() {
        var client = this.pos.get_client();
        this.$('.js_customer_name').text( client ? client.name : _t('Customer') );
    },
    click_set_customer: function(){
        this.gui.show_screen('clientlist');
    },
    click_back: function(){
        this.gui.show_screen('products');
    },
    renderElement: function() {
        var self = this;
        this._super();

        var numpad = this.render_numpad();
        numpad.appendTo(this.$('.payment-numpad'));

        var methods = this.render_paymentmethods();
        methods.appendTo(this.$('.paymentmethods-container'));

        this.render_paymentlines();

        this.$('.back').click(function(){
            self.click_back();
        });

        this.$('.next').click(function(){
            self.validate_order();
        });

        this.$('.js_set_customer').click(function(){
            self.click_set_customer();
        });

        this.$('.js_tip').click(function(){
            self.click_tip();
        });
        this.$('.js_invoice').click(function(){
            self.click_invoice();
        });
        this.$('.js_email').click(function(){
            self.click_email();
        });
        this.$('.js_cashdrawer').click(function(){
            self.pos.proxy.printer.open_cashbox();
        });

    },
    show: function(){
        this.pos.get_order().clean_empty_paymentlines();
        this.reset_input();
        this.render_paymentlines();
        // that one comes from BarcodeEvents
        $('body').keypress(this.keyboard_handler);
        // that one comes from the pos, but we prefer to cover all the basis
        $('body').keydown(this.keyboard_keydown_handler);
        this._super();
    },
    hide: function(){
        $('body').off('keypress', this.keyboard_handler);
        $('body').off('keydown', this.keyboard_keydown_handler);
        var order = this.pos.get_order();
        if (order) {
            order.stop_electronic_payment();
        }
        this._super();
    },
    // sets up listeners to watch for order changes
    watch_order_changes: function() {
        var self = this;
        var order = this.pos.get_order();
        if(this.old_order){
            this.old_order.stop_electronic_payment();
            // TODO jcb
            // This doesn't properly remove the bound events in the old_order
            // So when you switch back-and-forth between to orders, the on 'all'
            // events are duplicated several times.
            this.old_order.off(null, null, this);
            this.old_order.paymentlines.off(null, null, this);
        }
        if (!order) {
            return;
        }
        order.on('all',function(){
            self.order_changes();
        });
        order.paymentlines.on('all', self.order_changes.bind(self));
        this.old_order = order;
    },
    // called when the order is changed, used to show if
    // the order is paid or not
    order_changes: function(){
        var self = this;
        var order = this.pos.get_order();
        if (!order) {
            return;
        } else if (order.is_paid()) {
            self.$('.next').addClass('highlight');
        }else{
            self.$('.next').removeClass('highlight');
        }
    },

    order_is_valid: function(force_validation) {
        var self = this;
        var order = this.pos.get_order();

        // FIXME: this check is there because the backend is unable to
        // process empty orders. This is not the right place to fix it.
        if (order.get_orderlines().length === 0) {
            this.gui.show_popup('error',{
                'title': _t('Empty Order'),
                'body':  _t('There must be at least one product in your order before it can be validated'),
            });
            return false;
        }

        if (!order.is_paid() || this.invoicing) {
            return false;
        }

        if(order.has_not_valid_rounding()) {
            var line = order.has_not_valid_rounding();
            this.gui.show_popup('error',{
                    title: _t('Incorrect rounding'),
                    body:  _t('You have to round your payments lines.' + line.amount + ' is not rounded.'),
                });
            return false;
        }

        // The exact amount must be paid if there is no cash payment method defined.
        if (Math.abs(order.get_total_with_tax() - order.get_total_paid()) > 0.00001) {
            var cash = false;
            for (var i = 0; i < this.pos.payment_methods.length; i++) {
                cash = cash || (this.pos.payment_methods[i].is_cash_count);
            }
            if (!cash) {
                this.gui.show_popup('error',{
                    title: _t('Cannot return change without a cash payment method'),
                    body:  _t('There is no cash payment method available in this point of sale to handle the change.\n\n Please pay the exact amount or add a cash payment method in the point of sale configuration'),
                });
                return false;
            }
        }

        var client = order.get_client();
        if (order.is_to_email() && (!client || client && !utils.is_email(client.email))) {
            var title = !client
                ? 'Please select the customer'
                : 'Please provide valid email';
            var body = !client
                ? 'You need to select the customer before you can send the receipt via email.'
                : 'This customer does not have a valid email address, define one or do not send an email.';
            this.gui.show_popup('confirm', {
                'title': _t(title),
                'body': _t(body),
                confirm: function () {
                    this.gui.show_screen('clientlist');
                },
            });
            return false;
        }

        // if the change is too large, it's probably an input error, make the user confirm.
        if (!force_validation && order.get_total_with_tax() > 0 && (order.get_total_with_tax() * 1000 < order.get_total_paid())) {
            this.gui.show_popup('confirm',{
                title: _t('Please Confirm Large Amount'),
                body:  _t('Are you sure that the customer wants to  pay') + 
                       ' ' + 
                       this.format_currency(order.get_total_paid()) +
                       ' ' +
                       _t('for an order of') +
                       ' ' +
                       this.format_currency(order.get_total_with_tax()) +
                       ' ' +
                       _t('? Clicking "Confirm" will validate the payment.'),
                confirm: function() {
                    self.validate_order('confirm');
                },
            });
            return false;
        }

        return true;
    },

    finalize_validation: function() {
        var self = this;
        var order = this.pos.get_order();

        if (order.is_paid_with_cash() && this.pos.config.iface_cashdrawer) { 

                this.pos.proxy.printer.open_cashbox();
        }

        order.initialize_validation_date();
        order.finalized = true;

        if (order.is_to_invoice()) {
            var invoiced = this.pos.push_and_invoice_order(order);
            this.invoicing = true;

            invoiced.catch(this._handleFailedPushOrder.bind(this, order, false));

            invoiced.then(function (server_ids) {
                self.invoicing = false;
                var post_push_promise = [];
                post_push_promise = self.post_push_order_resolve(order, server_ids);
                post_push_promise.then(function () {
                        self.gui.show_screen('receipt');
                }).catch(function (error) {
                    self.gui.show_screen('receipt');
                    if (error) {
                        self.gui.show_popup('error',{
                            'title': "Error: no internet connection",
                            'body':  error,
                        });
                    }
                });
            });
        } else {
            var ordered = this.pos.push_order(order);
            if (order.wait_for_push_order()){
                var server_ids = [];
                ordered.catch(this._handleFailedPushOrder.bind(this, order, false));
                ordered.then(function (ids) {
                  server_ids = ids;
                }).finally(function() {
                    var post_push_promise = [];
                    post_push_promise = self.post_push_order_resolve(order, server_ids);
                    post_push_promise.then(function () {
                            self.gui.show_screen('receipt');
                        }).catch(function (error) {
                          self.gui.show_screen('receipt');
                          if (error) {
                              self.gui.show_popup('error',{
                                  'title': "Error: no internet connection",
                                  'body':  error,
                              });
                          }
                        });
                  });
            }
            else {
              self.gui.show_screen('receipt');
            }

        }

    },
    post_push_order_resolve: function(order, server_ids){
      var self = this;
      if (order.is_to_email()) {
          var email_promise = self.send_receipt_to_customer(server_ids);
          return email_promise;
      }
      else {
        return Promise.resolve();
      }
    },

    // Check if the order is paid, then sends it to the backend,
    // and complete the sale process
    validate_order: function(force_validation) {
        if (this.order_is_valid(force_validation)) {
            // remove pending payments before finalizing the validation
            var order = this.pos.get_order();
            order.get_paymentlines().forEach(line => {
                if (!line.is_done()) {
                    order.remove_paymentline(line);
                }
            });
            this.render_paymentlines();
            this.finalize_validation();
        }
    },

    send_receipt_to_customer: function(order_server_ids) {
        var order = this.pos.get_order();
        var data = {
            widget: this,
            pos: order.pos,
            order: order,
            receipt: order.export_for_printing(),
            orderlines: order.get_orderlines(),
            paymentlines: order.get_paymentlines(),
        };

        var receipt = QWeb.render('OrderReceipt', data);
        var printer = new Printer();

        return new Promise(function (resolve, reject) {
            printer.htmlToImg(receipt).then(function(ticket) {
                rpc.query({
                    model: 'pos.order',
                    method: 'action_receipt_to_customer',
                    args: [order_server_ids, order.get_name(), order.get_client(), ticket],
                }).then(function() {
                  resolve();
                }).catch(function () {
                  order.set_to_email(false);
                  reject("There is no internet connection, impossible to send the email.");
                });
            });
        });
    },
});
gui.define_screen({name:'payment', widget: PaymentScreenWidget});

var set_fiscal_position_button = ActionButtonWidget.extend({
    template: 'SetFiscalPositionButton',
    init: function (parent, options) {
        this._super(parent, options);

        this.pos.get('orders').on('add remove change', function () {
            this.renderElement();
        }, this);

        this.pos.on('change:selectedOrder', function () {
            this.renderElement();
        }, this);
    },
    button_click: function () {
        var self = this;

        var no_fiscal_position = [{
            label: _t("None"),
        }];
        var fiscal_positions = _.map(self.pos.fiscal_positions, function (fiscal_position) {
            return {
                label: fiscal_position.name,
                item: fiscal_position
            };
        });

        var selection_list = no_fiscal_position.concat(fiscal_positions);
        self.gui.show_popup('selection',{
            title: _t('Select Fiscal Position'),
            list: selection_list,
            confirm: function (fiscal_position) {
                var order = self.pos.get_order();
                order.fiscal_position = fiscal_position;
                // This will trigger the recomputation of taxes on order lines.
                // It is necessary to manually do it for the sake of consistency
                // with what happens when changing a customer. 
                _.each(order.orderlines.models, function (line) {
                    line.set_quantity(line.quantity);
                });
                order.trigger('change');
            },
            is_selected: function (fiscal_position) {
                return fiscal_position === self.pos.get_order().fiscal_position;
            }
        });
    },
    get_current_fiscal_position_name: function () {
        var name = _t('Tax');
        var order = this.pos.get_order();

        if (order) {
            var fiscal_position = order.fiscal_position;

            if (fiscal_position) {
                name = fiscal_position.display_name;
            }
        }
         return name;
    },
});

define_action_button({
    'name': 'set_fiscal_position',
    'widget': set_fiscal_position_button,
    'condition': function(){
        return this.pos.fiscal_positions.length > 0;
    },
});

var set_pricelist_button = ActionButtonWidget.extend({
    template: 'SetPricelistButton',
    init: function (parent, options) {
        this._super(parent, options);

        this.pos.get('orders').on('add remove change', function () {
            this.renderElement();
        }, this);

        this.pos.on('change:selectedOrder', function () {
            this.renderElement();
        }, this);
    },
    button_click: function () {
        var self = this;

        var pricelists = _.map(self.pos.pricelists, function (pricelist) {
            return {
                label: pricelist.name,
                item: pricelist
            };
        });

        self.gui.show_popup('selection',{
            title: _t('Select pricelist'),
            list: pricelists,
            confirm: function (pricelist) {
                var order = self.pos.get_order();
                order.set_pricelist(pricelist);
            },
            is_selected: function (pricelist) {
                return pricelist.id === self.pos.get_order().pricelist.id;
            }
        });
    },
    get_current_pricelist_name: function () {
        var name = _t('Pricelist');
        var order = this.pos.get_order();

        if (order) {
            var pricelist = order.pricelist;

            if (pricelist) {
                name = pricelist.display_name;
            }
        }
         return name;
    },
});

define_action_button({
    'name': 'set_pricelist',
    'widget': set_pricelist_button,
    'condition': function(){
        return this.pos.config.use_pricelist && this.pos.pricelists.length > 1;
    },
});

return {
    ActionButtonWidget: ActionButtonWidget,
    define_action_button: define_action_button,
    ScreenWidget: ScreenWidget,
    PaymentScreenWidget: PaymentScreenWidget,
    OrderWidget: OrderWidget,
    NumpadWidget: NumpadWidget,
    ProductScreenWidget: ProductScreenWidget,
    ActionpadWidget: ActionpadWidget,
    ScaleScreenWidget: ScaleScreenWidget,
    set_fiscal_position_button: set_fiscal_position_button,
    set_pricelist_button: set_pricelist_button,
};

});
