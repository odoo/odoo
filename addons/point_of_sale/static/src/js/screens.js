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
var models = require('point_of_sale.models');
var core = require('web.core');
var rpc = require('web.rpc');
var utils = require('web.utils');
var field_utils = require('web.field_utils');
var BarcodeEvents = require('barcodes.BarcodeEvents').BarcodeEvents;

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

    // what happens when a cashier id barcode is scanned.
    // the default behavior is the following : 
    // - if there's a user with a matching barcode, put it as the active 'cashier', go to cashier mode, and return true
    // - else : do nothing and return false. You probably want to extend this to show and appropriate error popup... 
    barcode_cashier_action: function(code){
        var self = this;
        var users = this.pos.users;
        for(var i = 0, len = users.length; i < len; i++){
            if(users[i].barcode === code.code){
                if (users[i].id !== this.pos.get_cashier().id && users[i].pos_security_pin) {
                    return this.gui.ask_password(users[i].pos_security_pin).then(function(){
                        self.pos.set_cashier(users[i]);
                        self.chrome.widget.username.renderElement();
                        return true;
                    });
                } else {
                    this.pos.set_cashier(users[i]);
                    this.chrome.widget.username.renderElement();
                    return true;
                }
            }
        }
        this.barcode_error_action(code);
        return false;
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
            'cashier': _.bind(self.barcode_cashier_action, self),
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
    _handleFailedPushForInvoice: function (order, refresh_screen, error) {
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
 |          THE DOM CACHE               |
\*======================================*/

// The Dom Cache is used by various screens to improve
// their performances when displaying many time the 
// same piece of DOM.
//
// It is a simple map from string 'keys' to DOM Nodes.
//
// The cache empties itself based on usage frequency 
// stats, so you may not always get back what
// you put in.

var DomCache = core.Class.extend({
    init: function(options){
        options = options || {};
        this.max_size = options.max_size || 2000;

        this.cache = {};
        this.access_time = {};
        this.size = 0;
    },
    cache_node: function(key,node){
        var cached = this.cache[key];
        this.cache[key] = node;
        this.access_time[key] = new Date().getTime();
        if(!cached){
            this.size++;
            while(this.size >= this.max_size){
                var oldest_key = null;
                var oldest_time = new Date().getTime();
                for(key in this.cache){
                    var time = this.access_time[key];
                    if(time <= oldest_time){
                        oldest_time = time;
                        oldest_key  = key;
                    }
                }
                if(oldest_key){
                    delete this.cache[oldest_key];
                    delete this.access_time[oldest_key];
                }
                this.size--;
            }
        }
        return node;
    },
    clear_node: function(key) {
        var cached = this.cache[key];
        if (cached) {
            delete this.cache[key];
            delete this.access_time[key];
            this.size --;
        }
    },
    get_node: function(key){
        var cached = this.cache[key];
        if(cached){
            this.access_time[key] = new Date().getTime();
        }
        return cached;
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
        var queue = this.pos.proxy_queue;

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


/* ------------ The Numpad ------------ */

// The numpad that edits the order lines.

var NumpadWidget = PosBaseWidget.extend({
    template:'NumpadWidget',
    init: function(parent) {
        this._super(parent);
        this.state = new models.NumpadState();
    },
    start: function() {
        this.applyAccessRights();
        this.state.bind('change:mode', this.changedMode, this);
        this.pos.bind('change:cashier', this.applyAccessRights, this);
        this.changedMode();
        this.$el.find('.numpad-backspace').click(_.bind(this.clickDeleteLastChar, this));
        this.$el.find('.numpad-minus').click(_.bind(this.clickSwitchSign, this));
        this.$el.find('.number-char').click(_.bind(this.clickAppendNewChar, this));
        this.$el.find('.mode-button').click(_.bind(this.clickChangeMode, this));
    },
    applyAccessRights: function() {
        var cashier = this.pos.get('cashier') || this.pos.get_cashier();
        var has_price_control_rights = !this.pos.config.restrict_price_control || cashier.role == 'manager';
        this.$el.find('.mode-button[data-mode="price"]')
            .toggleClass('disabled-mode', !has_price_control_rights)
            .prop('disabled', !has_price_control_rights);
        if (!has_price_control_rights && this.state.get('mode')=='price'){
            this.state.changeMode('quantity');
        }
    },
    clickDeleteLastChar: function() {
        return this.state.deleteLastChar();
    },
    clickSwitchSign: function() {
        return this.state.switchSign();
    },
    clickAppendNewChar: function(event) {
        var newChar;
        newChar = event.currentTarget.innerText || event.currentTarget.textContent;
        return this.state.appendNewChar(newChar);
    },
    clickChangeMode: function(event) {
        var newMode = event.currentTarget.attributes['data-mode'].nodeValue;
        return this.state.changeMode(newMode);
    },
    changedMode: function() {
        var mode = this.state.get('mode');
        $('.selected-mode').removeClass('selected-mode');
        $(_.str.sprintf('.mode-button[data-mode="%s"]', mode), this.$el).addClass('selected-mode');
    },
});

/* ---------- The Action Pad ---------- */

// The action pad contains the payment button and the 
// customer selection button

var ActionpadWidget = PosBaseWidget.extend({
    template: 'ActionpadWidget',
    init: function(parent, options) {
        var self = this;
        this._super(parent, options);

        this.pos.bind('change:selectedClient', function() {
            self.renderElement();
        });
    },
    renderElement: function() {
        var self = this;
        this._super();
        this.$('.pay').click(function(){
            var order = self.pos.get_order();
            var has_valid_product_lot = _.every(order.orderlines.models, function(line){
                return line.has_valid_product_lot();
            });
            if(!has_valid_product_lot){
                self.gui.show_popup('confirm',{
                    'title': _t('Empty Serial/Lot Number'),
                    'body':  _t('One or more product(s) required serial/lot number.'),
                    confirm: function(){
                        self.gui.show_screen('payment');
                    },
                });
            }else{
                self.gui.show_screen('payment');
            }
        });
        this.$('.set-customer').click(function(){
            self.gui.show_screen('clientlist');
        });
    }
});

/* --------- The Order Widget --------- */

// Displays the current Order.

var OrderWidget = PosBaseWidget.extend({
    template:'OrderWidget',
    init: function(parent, options) {
        var self = this;
        this._super(parent,options);

        this.numpad_state = options.numpad_state;
        this.numpad_state.reset();
        this.numpad_state.bind('set_value',   this.set_value, this);

        this.pos.bind('change:selectedOrder', this.change_selected_order, this);

        this.line_click_handler = function(event){
            self.click_line(this.orderline, event);
        };

        if (this.pos.get_order()) {
            this.bind_order_events();
        }

    },
    click_line: function(orderline, event) {
        this.pos.get_order().select_orderline(orderline);
        this.numpad_state.reset();
    },


    set_value: function(val) {
    	var order = this.pos.get_order();
    	if (order.get_selected_orderline()) {
            var mode = this.numpad_state.get('mode');
            if( mode === 'quantity'){
                order.get_selected_orderline().set_quantity(val);
            }else if( mode === 'discount'){
                order.get_selected_orderline().set_discount(val);
            }else if( mode === 'price'){
                var selected_orderline = order.get_selected_orderline();
                selected_orderline.price_manually_set = true;
                selected_orderline.set_unit_price(val);
            }
    	}
    },
    change_selected_order: function() {
        if (this.pos.get_order()) {
            this.bind_order_events();
            this.numpad_state.reset();
            this.renderElement();
        }
    },
    orderline_add: function(){
        this.numpad_state.reset();
        this.renderElement('and_scroll_to_bottom');
    },
    orderline_remove: function(line){
        this.remove_orderline(line);
        this.numpad_state.reset();
        this.update_summary();
    },
    orderline_change: function(line){
        this.rerender_orderline(line);
        this.update_summary();
    },
    bind_order_events: function() {
        var order = this.pos.get_order();
            order.unbind('change:client', this.update_summary, this);
            order.bind('change:client',   this.update_summary, this);
            order.unbind('change',        this.update_summary, this);
            order.bind('change',          this.update_summary, this);

        var lines = order.orderlines;
            lines.unbind('add',     this.orderline_add,    this);
            lines.bind('add',       this.orderline_add,    this);
            lines.unbind('remove',  this.orderline_remove, this);
            lines.bind('remove',    this.orderline_remove, this); 
            lines.unbind('change',  this.orderline_change, this);
            lines.bind('change',    this.orderline_change, this);

    },
    render_orderline: function(orderline){
        var el_str  = QWeb.render('Orderline',{widget:this, line:orderline}); 
        var el_node = document.createElement('div');
            el_node.innerHTML = _.str.trim(el_str);
            el_node = el_node.childNodes[0];
            el_node.orderline = orderline;
            el_node.addEventListener('click',this.line_click_handler);
        var el_lot_icon = el_node.querySelector('.line-lot-icon');
        if(el_lot_icon){
            el_lot_icon.addEventListener('click', (function() {
                this.show_product_lot(orderline);
            }.bind(this)));
        }

        orderline.node = el_node;
        return el_node;
    },
    remove_orderline: function(order_line){
        if(this.pos.get_order().get_orderlines().length === 0){
            this.renderElement();
        }else{
            order_line.node.parentNode.removeChild(order_line.node);
        }
    },
    rerender_orderline: function(order_line){
        var node = order_line.node;
        var replacement_line = this.render_orderline(order_line);
        node.parentNode.replaceChild(replacement_line,node);
    },
    // overriding the openerp framework replace method for performance reasons
    replace: function($target){
        this.renderElement();
        var target = $target[0];
        target.parentNode.replaceChild(this.el,target);
    },
    renderElement: function(scrollbottom){
        var order  = this.pos.get_order();
        if (!order) {
            return;
        }
        var orderlines = order.get_orderlines();

        var el_str  = QWeb.render('OrderWidget',{widget:this, order:order, orderlines:orderlines});

        var el_node = document.createElement('div');
            el_node.innerHTML = _.str.trim(el_str);
            el_node = el_node.childNodes[0];


        var list_container = el_node.querySelector('.orderlines');
        for(var i = 0, len = orderlines.length; i < len; i++){
            var orderline = this.render_orderline(orderlines[i]);
            list_container.appendChild(orderline);
        }

        if(this.el && this.el.parentNode){
            this.el.parentNode.replaceChild(el_node,this.el);
        }
        this.el = el_node;
        this.update_summary();

        if(scrollbottom){
            this.el.querySelector('.order-scroller').scrollTop = 100 * orderlines.length;
        }
    },
    update_summary: function(){
        var order = this.pos.get_order();
        if (!order.get_orderlines().length) {
            return;
        }

        var total     = order ? order.get_total_with_tax() : 0;
        var taxes     = order ? total - order.get_total_without_tax() : 0;

        this.el.querySelector('.summary .total > .value').textContent = this.format_currency(total);
        this.el.querySelector('.summary .total .subentry .value').textContent = this.format_currency(taxes);
    },
    show_product_lot: function(orderline){
        this.pos.get_order().select_orderline(orderline);
        var order = this.pos.get_order();
        order.display_lot_popup();
    },
});

/* ------ The Product Categories ------ */

// Display and navigate the product categories.
// Also handles searches.
//  - set_category() to change the displayed category
//  - reset_category() to go to the root category
//  - perform_search() to search for products
//  - clear_search()   does what it says.

var ProductCategoriesWidget = PosBaseWidget.extend({
    template: 'ProductCategoriesWidget',
    init: function(parent, options){
        var self = this;
        this._super(parent,options);
        this.product_type = options.product_type || 'all';  // 'all' | 'weightable'
        this.onlyWeightable = options.onlyWeightable || false;
        this.category = this.pos.root_category;
        this.breadcrumb = [];
        this.subcategories = [];
        this.product_list_widget = options.product_list_widget || null;
        this.category_cache = new DomCache();
        this.start_categ_id = this.pos.config.iface_start_categ_id ? this.pos.config.iface_start_categ_id[0] : 0;
        this.set_category(this.pos.db.get_category_by_id(this.start_categ_id));
        
        this.switch_category_handler = function(event){
            self.set_category(self.pos.db.get_category_by_id(Number(this.dataset.categoryId)));
            self.renderElement();
        };
        
        this.clear_search_handler = function(event){
            self.clear_search();
        };

        var search_timeout  = null;
        this.search_handler = function(event){
            if(event.type == "keypress" || event.keyCode === 46 || event.keyCode === 8){
                clearTimeout(search_timeout);

                var searchbox = this;

                search_timeout = setTimeout(function(){
                    self.perform_search(self.category, searchbox.value, event.which === 13);
                },70);
            }
        };
    },

    // changes the category. if undefined, sets to root category
    set_category : function(category){
        var db = this.pos.db;
        if(!category){
            this.category = db.get_category_by_id(db.root_category_id);
        }else{
            this.category = category;
        }
        this.breadcrumb = [];
        var ancestors_ids = db.get_category_ancestors_ids(this.category.id);
        for(var i = 1; i < ancestors_ids.length; i++){
            this.breadcrumb.push(db.get_category_by_id(ancestors_ids[i]));
        }
        if(this.category.id !== db.root_category_id){
            this.breadcrumb.push(this.category);
        }
        this.subcategories = db.get_category_by_id(db.get_category_childs_ids(this.category.id));
    },

    get_image_url: function(category){
        return window.location.origin + '/web/image?model=pos.category&field=image_medium&id='+category.id;
    },

    render_category: function( category, with_image ){
        var cached = this.category_cache.get_node(category.id);
        if(!cached){
            if(with_image){
                var image_url = this.get_image_url(category);
                var category_html = QWeb.render('CategoryButton',{ 
                        widget:  this, 
                        category: category, 
                        image_url: this.get_image_url(category),
                    });
                    category_html = _.str.trim(category_html);
                var category_node = document.createElement('div');
                    category_node.innerHTML = category_html;
                    category_node = category_node.childNodes[0];
            }else{
                var category_html = QWeb.render('CategorySimpleButton',{ 
                        widget:  this, 
                        category: category, 
                    });
                    category_html = _.str.trim(category_html);
                var category_node = document.createElement('div');
                    category_node.innerHTML = category_html;
                    category_node = category_node.childNodes[0];
            }
            this.category_cache.cache_node(category.id,category_node);
            return category_node;
        }
        return cached; 
    },

    replace: function($target){
        this.renderElement();
        var target = $target[0];
        target.parentNode.replaceChild(this.el,target);
    },

    renderElement: function(){

        var el_str  = QWeb.render(this.template, {widget: this});
        var el_node = document.createElement('div');

        el_node.innerHTML = el_str;
        el_node = el_node.childNodes[1];

        if(this.el && this.el.parentNode){
            this.el.parentNode.replaceChild(el_node,this.el);
        }

        this.el = el_node;

        var withpics = this.pos.config.iface_display_categ_images;

        var list_container = el_node.querySelector('.category-list');
        if (list_container) { 
            if (!withpics) {
                list_container.classList.add('simple');
            } else {
                list_container.classList.remove('simple');
            }
            for(var i = 0, len = this.subcategories.length; i < len; i++){
                list_container.appendChild(this.render_category(this.subcategories[i],withpics));
            }
        }

        var buttons = el_node.querySelectorAll('.js-category-switch');
        for(var i = 0; i < buttons.length; i++){
            buttons[i].addEventListener('click',this.switch_category_handler);
        }

        var products = this.pos.db.get_product_by_category(this.category.id); 
        this.product_list_widget.set_product_list(products); // FIXME: this should be moved elsewhere ... 

        this.el.querySelector('.searchbox input').addEventListener('keypress',this.search_handler);

        this.el.querySelector('.searchbox input').addEventListener('keydown',this.search_handler);

        this.el.querySelector('.search-clear').addEventListener('click',this.clear_search_handler);

        if(this.pos.config.iface_vkeyboard && this.chrome.widget.keyboard){
            this.chrome.widget.keyboard.connect($(this.el.querySelector('.searchbox input')));
        }
    },
    
    // resets the current category to the root category
    reset_category: function(){
        this.set_category(this.pos.db.get_category_by_id(this.start_categ_id));
        this.renderElement();
    },

    // empties the content of the search box
    clear_search: function(){
        var products = this.pos.db.get_product_by_category(this.category.id);
        this.product_list_widget.set_product_list(products);
        var input = this.el.querySelector('.searchbox input');
            input.value = '';
            input.focus();
    },
    perform_search: function(category, query, buy_result){
        var products;
        if(query){
            products = this.pos.db.search_product_in_category(category.id,query);
            if(buy_result && products.length === 1){
                    this.pos.get_order().add_product(products[0]);
                    this.clear_search();
            }else{
                this.product_list_widget.set_product_list(products);
            }
        }else{
            products = this.pos.db.get_product_by_category(this.category.id);
            this.product_list_widget.set_product_list(products);
        }
    },

});

/* --------- The Product List --------- */

// Display the list of products. 
// - change the list with .set_product_list()
// - click_product_action(), passed as an option, tells
//   what to do when a product is clicked. 

var ProductListWidget = PosBaseWidget.extend({
    template:'ProductListWidget',
    init: function(parent, options) {
        var self = this;
        this._super(parent,options);
        this.model = options.model;
        this.productwidgets = [];
        this.weight = options.weight || 0;
        this.show_scale = options.show_scale || false;
        this.next_screen = options.next_screen || false;

        this.click_product_handler = function(){
            var product = self.pos.db.get_product_by_id(this.dataset.productId);
            options.click_product_action(product);
        };

        this.keypress_product_handler = function(ev){
            // React only to SPACE to avoid interfering with warcode scanner which sends ENTER
            if (ev.which != 32) {
                return;
            }
            ev.preventDefault();
            var product = self.pos.db.get_product_by_id(this.dataset.productId);
            options.click_product_action(product);
        };

        this.product_list = options.product_list || [];
        this.product_cache = new DomCache();

        this.pos.get('orders').bind('add remove change', function () {
            self.renderElement();
        }, this);

        this.pos.bind('change:selectedOrder', function () {
            this.renderElement();
        }, this);
    },
    set_product_list: function(product_list){
        this.product_list = product_list;
        this.renderElement();
    },
    get_product_image_url: function(product){
        return window.location.origin + '/web/image?model=product.product&field=image_medium&id='+product.id;
    },
    replace: function($target){
        this.renderElement();
        var target = $target[0];
        target.parentNode.replaceChild(this.el,target);
    },
    calculate_cache_key: function(product, pricelist){
        return product.id + ',' + pricelist.id;
    },
    _get_active_pricelist: function(){
        var current_order = this.pos.get_order();
        var current_pricelist = this.pos.default_pricelist;

        if (current_order) {
            current_pricelist = current_order.pricelist;
        }

        return current_pricelist;
    },
    render_product: function(product){
        var current_pricelist = this._get_active_pricelist();
        var cache_key = this.calculate_cache_key(product, current_pricelist);
        var cached = this.product_cache.get_node(cache_key);
        if(!cached){
            var image_url = this.get_product_image_url(product);
            var product_html = QWeb.render('Product',{ 
                    widget:  this, 
                    product: product,
                    pricelist: current_pricelist,
                    image_url: this.get_product_image_url(product),
                });
            var product_node = document.createElement('div');
            product_node.innerHTML = product_html;
            product_node = product_node.childNodes[1];
            this.product_cache.cache_node(cache_key,product_node);
            return product_node;
        }
        return cached;
    },

    renderElement: function() {
        var el_str  = QWeb.render(this.template, {widget: this});
        var el_node = document.createElement('div');
            el_node.innerHTML = el_str;
            el_node = el_node.childNodes[1];

        if(this.el && this.el.parentNode){
            this.el.parentNode.replaceChild(el_node,this.el);
        }
        this.el = el_node;

        var list_container = el_node.querySelector('.product-list');
        for(var i = 0, len = this.product_list.length; i < len; i++){
            var product_node = this.render_product(this.product_list[i]);
            product_node.addEventListener('click',this.click_product_handler);
            product_node.addEventListener('keypress',this.keypress_product_handler);
            list_container.appendChild(product_node);
        }
    },
});

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

    start: function(){ 

        var self = this;

        this.actionpad = new ActionpadWidget(this,{});
        this.actionpad.replace(this.$('.placeholder-ActionpadWidget'));

        this.numpad = new NumpadWidget(this,{});
        this.numpad.replace(this.$('.placeholder-NumpadWidget'));

        this.order_widget = new OrderWidget(this,{
            numpad_state: this.numpad.state,
        });
        this.order_widget.replace(this.$('.placeholder-OrderWidget'));

        this.product_list_widget = new ProductListWidget(this,{
            click_product_action: function(product){ self.click_product(product); },
            product_list: this.pos.db.get_product_by_category(0)
        });
        this.product_list_widget.replace(this.$('.placeholder-ProductListWidget'));

        this.product_categories_widget = new ProductCategoriesWidget(this,{
            product_list_widget: this.product_list_widget,
        });
        this.product_categories_widget.replace(this.$('.placeholder-ProductCategoriesWidget'));

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
            this.product_categories_widget.reset_category();
            this.numpad.state.reset();
        }
        if (this.pos.config.iface_vkeyboard && this.chrome.widget.keyboard) {
            this.chrome.widget.keyboard.connect($(this.el.querySelector('.searchbox input')));
        }
    },

    close: function(){
        this._super();
        if(this.pos.config.iface_vkeyboard && this.chrome.widget.keyboard){
            this.chrome.widget.keyboard.hide();
        }
    },
});
gui.define_screen({name:'products', widget: ProductScreenWidget});

/*--------------------------------------*\
 |         THE CLIENT LIST              |
\*======================================*/

// The clientlist displays the list of customer,
// and allows the cashier to create, edit and assign
// customers.

var ClientListScreenWidget = ScreenWidget.extend({
    template: 'ClientListScreenWidget',

    init: function(parent, options){
        this._super(parent, options);
        this.partner_cache = new DomCache();
    },

    auto_back: true,

    show: function(){
        var self = this;
        this._super();

        this.renderElement();
        this.details_visible = false;
        this.old_client = this.pos.get_order().get_client();

        this.$('.back').click(function(){
            self.gui.back();
        });

        this.$('.next').click(function(){   
            self.save_changes();
            self.gui.back();    // FIXME HUH ?
        });

        this.$('.new-customer').click(function(){
            self.display_client_details('edit',{
                'country_id': self.pos.company.country_id,
            });
        });

        var partners = this.pos.db.get_partners_sorted(1000);
        this.render_list(partners);
        
        this.reload_partners();

        if( this.old_client ){
            this.display_client_details('show',this.old_client,0);
        }

        this.$('.client-list-contents').delegate('.client-line','click',function(event){
            self.line_select(event,$(this),parseInt($(this).data('id')));
        });

        var search_timeout = null;

        if(this.pos.config.iface_vkeyboard && this.chrome.widget.keyboard){
            this.chrome.widget.keyboard.connect(this.$('.searchbox input'));
        }

        this.$('.searchbox input').on('keypress',function(event){
            clearTimeout(search_timeout);

            var searchbox = this;

            search_timeout = setTimeout(function(){
                self.perform_search(searchbox.value, event.which === 13);
            },70);
        });

        this.$('.searchbox .search-clear').click(function(){
            self.clear_search();
        });
    },
    hide: function () {
        this._super();
        this.new_client = null;
    },
    barcode_client_action: function(code){
        if (this.editing_client) {
            this.$('.detail.barcode').val(code.code);
        } else if (this.pos.db.get_partner_by_barcode(code.code)) {
            var partner = this.pos.db.get_partner_by_barcode(code.code);
            this.new_client = partner;
            this.display_client_details('show', partner);
        }
    },
    perform_search: function(query, associate_result){
        var customers;
        if(query){
            customers = this.pos.db.search_partner(query);
            this.display_client_details('hide');
            if ( associate_result && customers.length === 1){
                this.new_client = customers[0];
                this.save_changes();
                this.gui.back();
            }
            this.render_list(customers);
        }else{
            customers = this.pos.db.get_partners_sorted();
            this.render_list(customers);
        }
    },
    clear_search: function(){
        var customers = this.pos.db.get_partners_sorted(1000);
        this.render_list(customers);
        this.$('.searchbox input')[0].value = '';
        this.$('.searchbox input').focus();
    },
    render_list: function(partners){
        var contents = this.$el[0].querySelector('.client-list-contents');
        contents.innerHTML = "";
        for(var i = 0, len = Math.min(partners.length,1000); i < len; i++){
            var partner    = partners[i];
            var clientline = this.partner_cache.get_node(partner.id);
            if(!clientline){
                var clientline_html = QWeb.render('ClientLine',{widget: this, partner:partners[i]});
                var clientline = document.createElement('tbody');
                clientline.innerHTML = clientline_html;
                clientline = clientline.childNodes[1];
                this.partner_cache.cache_node(partner.id,clientline);
            }
            if( partner === this.old_client ){
                clientline.classList.add('highlight');
            }else{
                clientline.classList.remove('highlight');
            }
            contents.appendChild(clientline);
        }
    },
    save_changes: function(){
        var order = this.pos.get_order();
        if( this.has_client_changed() ){
            var default_fiscal_position_id = _.findWhere(this.pos.fiscal_positions, {'id': this.pos.config.default_fiscal_position_id[0]});
            if ( this.new_client ) {
                if (this.new_client.property_account_position_id ){
                  var client_fiscal_position_id = _.findWhere(this.pos.fiscal_positions, {'id': this.new_client.property_account_position_id[0]});
                  order.fiscal_position = client_fiscal_position_id || default_fiscal_position_id;
                }
                order.set_pricelist(_.findWhere(this.pos.pricelists, {'id': this.new_client.property_product_pricelist[0]}) || this.pos.default_pricelist);
            } else {
                order.fiscal_position = default_fiscal_position_id;
                order.set_pricelist(this.pos.default_pricelist);
            }

            order.set_client(this.new_client);
        }
    },
    has_client_changed: function(){
        if( this.old_client && this.new_client ){
            return this.old_client.id !== this.new_client.id;
        }else{
            return !!this.old_client !== !!this.new_client;
        }
    },
    toggle_save_button: function(){
        var $button = this.$('.button.next');
        if (this.editing_client) {
            $button.addClass('oe_hidden');
            return;
        } else if( this.new_client ){
            if( !this.old_client){
                $button.text(_t('Set Customer'));
            }else{
                $button.text(_t('Change Customer'));
            }
        }else{
            $button.text(_t('Deselect Customer'));
        }
        $button.toggleClass('oe_hidden',!this.has_client_changed());
    },
    line_select: function(event,$line,id){
        var partner = this.pos.db.get_partner_by_id(id);
        this.$('.client-list .lowlight').removeClass('lowlight');
        if ( $line.hasClass('highlight') ){
            $line.removeClass('highlight');
            $line.addClass('lowlight');
            this.display_client_details('hide',partner);
            this.new_client = null;
            this.toggle_save_button();
        }else{
            this.$('.client-list .highlight').removeClass('highlight');
            $line.addClass('highlight');
            var y = event.pageY - $line.parent().offset().top;
            this.display_client_details('show',partner,y);
            this.new_client = partner;
            this.toggle_save_button();
        }
    },
    partner_icon_url: function(id){
        return '/web/image?model=res.partner&id='+id+'&field=image_small';
    },

    // ui handle for the 'edit selected customer' action
    edit_client_details: function(partner) {
        this.display_client_details('edit',partner);
    },

    // ui handle for the 'cancel customer edit changes' action
    undo_client_details: function(partner) {
        if (!partner.id) {
            this.display_client_details('hide');
        } else {
            this.display_client_details('show',partner);
        }
    },

    // what happens when we save the changes on the client edit form -> we fetch the fields, sanitize them,
    // send them to the backend for update, and call saved_client_details() when the server tells us the
    // save was successfull.
    save_client_details: function(partner) {
        var self = this;
        
        var fields = {};
        this.$('.client-details-contents .detail').each(function(idx,el){
            fields[el.name] = el.value || false;
        });

        if (!fields.name) {
            this.gui.show_popup('error',_t('A Customer Name Is Required'));
            return;
        }
        
        if (this.uploaded_picture) {
            fields.image = this.uploaded_picture;
        }

        fields.id           = partner.id || false;
        fields.country_id   = fields.country_id || false;

        if (fields.property_product_pricelist) {
            fields.property_product_pricelist = parseInt(fields.property_product_pricelist, 10);
        } else {
            fields.property_product_pricelist = false;
        }
        var contents = this.$(".client-details-contents");
        contents.off("click", ".button.save");


        rpc.query({
                model: 'res.partner',
                method: 'create_from_ui',
                args: [fields],
            })
            .then(function(partner_id){
                self.saved_client_details(partner_id);
            },function(err,ev){
                ev.preventDefault();
                var error_body = _t('Your Internet connection is probably down.');
                if (err.data) {
                    var except = err.data;
                    error_body = except.arguments && except.arguments[0] || except.message || error_body;
                }
                self.gui.show_popup('error',{
                    'title': _t('Error: Could not Save Changes'),
                    'body': error_body,
                });
                contents.on('click','.button.save',function(){ self.save_client_details(partner); });
            });
    },
    
    // what happens when we've just pushed modifications for a partner of id partner_id
    saved_client_details: function(partner_id){
        var self = this;
        return this.reload_partners().then(function(){
            var partner = self.pos.db.get_partner_by_id(partner_id);
            if (partner) {
                self.new_client = partner;
                self.toggle_save_button();
                self.display_client_details('show',partner);
            } else {
                // should never happen, because create_from_ui must return the id of the partner it
                // has created, and reload_partner() must have loaded the newly created partner. 
                self.display_client_details('hide');
            }
        }).always(function(){
            $(".client-details-contents").on('click','.button.save',function(){ self.save_client_details(partner); });
        });
    },

    // resizes an image, keeping the aspect ratio intact,
    // the resize is useful to avoid sending 12Mpixels jpegs
    // over a wireless connection.
    resize_image_to_dataurl: function(img, maxwidth, maxheight, callback){
        img.onload = function(){
            var canvas = document.createElement('canvas');
            var ctx    = canvas.getContext('2d');
            var ratio  = 1;

            if (img.width > maxwidth) {
                ratio = maxwidth / img.width;
            }
            if (img.height * ratio > maxheight) {
                ratio = maxheight / img.height;
            }
            var width  = Math.floor(img.width * ratio);
            var height = Math.floor(img.height * ratio);

            canvas.width  = width;
            canvas.height = height;
            ctx.drawImage(img,0,0,width,height);

            var dataurl = canvas.toDataURL();
            callback(dataurl);
        };
    },

    // Loads and resizes a File that contains an image.
    // callback gets a dataurl in case of success.
    load_image_file: function(file, callback){
        var self = this;
        if (!file.type.match(/image.*/)) {
            this.gui.show_popup('error',{
                title: _t('Unsupported File Format'),
                body:  _t('Only web-compatible Image formats such as .png or .jpeg are supported'),
            });
            return;
        }
        
        var reader = new FileReader();
        reader.onload = function(event){
            var dataurl = event.target.result;
            var img     = new Image();
            img.src = dataurl;
            self.resize_image_to_dataurl(img,800,600,callback);
        };
        reader.onerror = function(){
            self.gui.show_popup('error',{
                title :_t('Could Not Read Image'),
                body  :_t('The provided file could not be read due to an unknown error'),
            });
        };
        reader.readAsDataURL(file);
    },

    // This fetches partner changes on the server, and in case of changes, 
    // rerenders the affected views
    reload_partners: function(){
        var self = this;
        return this.pos.load_new_partners().then(function(){
            // partners may have changed in the backend
            self.partner_cache = new DomCache();

            self.render_list(self.pos.db.get_partners_sorted(1000));
            
            // update the currently assigned client if it has been changed in db.
            var curr_client = self.pos.get_order().get_client();
            if (curr_client) {
                self.pos.get_order().set_client(self.pos.db.get_partner_by_id(curr_client.id));
            }
        });
    },

    // Shows,hides or edit the customer details box :
    // visibility: 'show', 'hide' or 'edit'
    // partner:    the partner object to show or edit
    // clickpos:   the height of the click on the list (in pixel), used
    //             to maintain consistent scroll.
    display_client_details: function(visibility,partner,clickpos){
        var self = this;
        var searchbox = this.$('.searchbox input');
        var contents = this.$('.client-details-contents');
        var parent   = this.$('.client-list').parent();
        var scroll   = parent.scrollTop();
        var height   = contents.height();

        contents.off('click','.button.edit'); 
        contents.off('click','.button.save'); 
        contents.off('click','.button.undo'); 
        contents.on('click','.button.edit',function(){ self.edit_client_details(partner); });
        contents.on('click','.button.save',function(){ self.save_client_details(partner); });
        contents.on('click','.button.undo',function(){ self.undo_client_details(partner); });
        this.editing_client = false;
        this.uploaded_picture = null;

        if(visibility === 'show'){
            contents.empty();
            contents.append($(QWeb.render('ClientDetails',{widget:this,partner:partner})));

            var new_height   = contents.height();

            if(!this.details_visible){
                // resize client list to take into account client details
                parent.height('-=' + new_height);

                if(clickpos < scroll + new_height + 20 ){
                    parent.scrollTop( clickpos - 20 );
                }else{
                    parent.scrollTop(parent.scrollTop() + new_height);
                }
            }else{
                parent.scrollTop(parent.scrollTop() - height + new_height);
            }

            this.details_visible = true;
            this.toggle_save_button();
        } else if (visibility === 'edit') {
            // Connect the keyboard to the edited field
            if (this.pos.config.iface_vkeyboard && this.chrome.widget.keyboard) {
                contents.off('click', '.detail');
                searchbox.off('click');
                contents.on('click', '.detail', function(ev){
                    self.chrome.widget.keyboard.connect(ev.target);
                    self.chrome.widget.keyboard.show();
                });
                searchbox.on('click', function() {
                    self.chrome.widget.keyboard.connect($(this));
                });
            }

            this.editing_client = true;
            contents.empty();
            contents.append($(QWeb.render('ClientDetailsEdit',{widget:this,partner:partner})));
            this.toggle_save_button();

            // Browsers attempt to scroll invisible input elements
            // into view (eg. when hidden behind keyboard). They don't
            // seem to take into account that some elements are not
            // scrollable.
            contents.find('input').blur(function() {
                setTimeout(function() {
                    self.$('.window').scrollTop(0);
                }, 0);
            });

            contents.find('.image-uploader').on('change',function(event){
                if (event.target.files.length) {
                    self.load_image_file(event.target.files[0],function(res){
                        if (res) {
                            contents.find('.client-picture img, .client-picture .fa').remove();
                            contents.find('.client-picture').append("<img src='"+res+"'>");
                            contents.find('.detail.picture').remove();
                            self.uploaded_picture = res;
                        }
                    });
                }
            });
        } else if (visibility === 'hide') {
            contents.empty();
            parent.height('100%');
            if( height > scroll ){
                contents.css({height:height+'px'});
                contents.animate({height:0},400,function(){
                    contents.css({height:''});
                });
            }else{
                parent.scrollTop( parent.scrollTop() - height);
            }
            this.details_visible = false;
            this.toggle_save_button();
        }
    },
    close: function(){
        this._super();
        if (this.pos.config.iface_vkeyboard && this.chrome.widget.keyboard) {
            this.chrome.widget.keyboard.hide();
        }
    },
});
gui.define_screen({name:'clientlist', widget: ClientListScreenWidget});

/*--------------------------------------*\
 |         THE RECEIPT SCREEN           |
\*======================================*/

// The receipt screen displays the order's
// receipt and allows it to be printed in a web browser.
// The receipt screen is not shown if the point of sale
// is set up to print with the proxy. Altough it could
// be useful to do so...

var ReceiptScreenWidget = ScreenWidget.extend({
    template: 'ReceiptScreenWidget',
    show: function(){
        this._super();
        var self = this;

        this.render_change();
        this.render_receipt();
        this.handle_auto_print();
    },
    handle_auto_print: function() {
        if (this.should_auto_print()) {
            this.print();
            if (this.should_close_immediately()){
                this.click_next();
            }
        } else {
            this.lock_screen(false);
        }
    },
    should_auto_print: function() {
        return this.pos.config.iface_print_auto && !this.pos.get_order()._printed;
    },
    should_close_immediately: function() {
        var order = this.pos.get_order();
        var invoiced_finalized = order.is_to_invoice() ? order.finalized : true;
        return this.pos.config.iface_print_via_proxy && this.pos.config.iface_print_skip_screen && invoiced_finalized;
    },
    lock_screen: function(locked) {
        this._locked = locked;
        if (locked) {
            this.$('.next').removeClass('highlight');
        } else {
            this.$('.next').addClass('highlight');
        }
    },
    get_receipt_render_env: function() {
        var order = this.pos.get_order();
        return {
            widget: this,
            pos: this.pos,
            order: order,
            receipt: order.export_for_printing(),
            orderlines: order.get_orderlines(),
            paymentlines: order.get_paymentlines(),
        };
    },
    print_web: function() {
        if ($.browser.safari) {
            document.execCommand('print', false, null);
        } else {
            try {
                window.print();
            } catch(err) {
                if (navigator.userAgent.toLowerCase().indexOf("android") > -1) {
                    this.gui.show_popup('error',{
                        'title':_t('Printing is not supported on some android browsers'),
                        'body': _t('Printing is not supported on some android browsers due to no default printing protocol is available. It is possible to print your tickets by making use of an IoT Box.'),
                    });
                } else {
                    throw err;
                }
            }
        }
        this.pos.get_order()._printed = true;
    },
    print_xml: function() {
        var receipt = QWeb.render('XmlReceipt', this.get_receipt_render_env());

        this.pos.proxy.print_receipt(receipt);
        this.pos.get_order()._printed = true;
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
        this.pos.get_order().finalize();
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
    render_change: function() {
        var self = this;
        this.$('.change-value').html(this.format_currency(this.pos.get_order().get_change()));
        var order = this.pos.get_order();
        var order_screen_params = order.get_screen_data('params');
        var button_print_invoice = this.$('h2.print_invoice');
        if (order_screen_params && order_screen_params.button_print_invoice) {
            button_print_invoice.show();
        } else {
            button_print_invoice.hide();
        }
    },
    render_receipt: function() {
        this.$('.pos-receipt-container').html(QWeb.render('PosTicket', this.get_receipt_render_env()));
    },
});
gui.define_screen({name:'receipt', widget: ReceiptScreenWidget});

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

        this.pos.bind('change:selectedOrder',function(){
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
                            event.keyCode === 44 ||  // Comma
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

        this.pos.bind('change:selectedClient', function() {
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
        var newbuf = this.gui.numpad_input(this.inputbuffer, input, {'firstinput': this.firstinput});

        this.firstinput = (newbuf.length === 0);

        // popup block inputs to prevent sneak editing. 
        if (this.gui.has_popup()) {
            return;
        }
        
        if (newbuf !== this.inputbuffer) {
            this.inputbuffer = newbuf;
            var order = this.pos.get_order();
            if (order.selected_paymentline) {
                var amount = this.inputbuffer;

                if (this.inputbuffer !== "-") {
                    amount = field_utils.parse.float(this.inputbuffer);
                }

                order.selected_paymentline.set_amount(amount);
                this.order_changes();
                this.render_paymentlines();
                this.$('.paymentline.selected .edit').text(this.format_currency_no_symbol(amount));
            }
        }
    },
    click_numpad: function(button) {
	var paymentlines = this.pos.get_order().get_paymentlines();
	var open_paymentline = false;

	for (var i = 0; i < paymentlines.length; i++) {
	    if (! paymentlines[i].paid) {
		open_paymentline = true;
	    }
	}

	if (! open_paymentline) {
            this.pos.get_order().add_paymentline( this.pos.cashregisters[0]);
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
            if (lines[i].cid === cid) {
                this.pos.get_order().remove_paymentline(lines[i]);
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
    render_paymentlines: function() {
        var self  = this;
        var order = this.pos.get_order();
        if (!order) {
            return;
        }

        var lines = order.get_paymentlines();
        var due   = order.get_due();
        var extradue = 0;
        if (due && lines.length  && due !== order.get_due(lines[lines.length-1])) {
            extradue = due;
        }


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
    },
    click_paymentmethods: function(id) {
        var cashregister = null;
        for ( var i = 0; i < this.pos.cashregisters.length; i++ ) {
            if ( this.pos.cashregisters[i].journal_id[0] === id ){
                cashregister = this.pos.cashregisters[i];
                break;
            }
        }
        this.pos.get_order().add_paymentline( cashregister );
        this.reset_input();
        this.render_paymentlines();
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
                self.order_changes();
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

        this.$('.js_cashdrawer').click(function(){
            self.pos.proxy.open_cashbox();
        });

    },
    show: function(){
        this.pos.get_order().clean_empty_paymentlines();
        this.reset_input();
        this.render_paymentlines();
        this.order_changes();
        // that one comes from BarcodeEvents
        $('body').keypress(this.keyboard_handler);
        // that one comes from the pos, but we prefer to cover all the basis
        $('body').keydown(this.keyboard_keydown_handler);
        this._super();
    },
    hide: function(){
        $('body').off('keypress', this.keyboard_handler);
        $('body').off('keydown', this.keyboard_keydown_handler);
        this._super();
    },
    // sets up listeners to watch for order changes
    watch_order_changes: function() {
        var self = this;
        var order = this.pos.get_order();
        if (!order) {
            return;
        }
        if(this.old_order){
            this.old_order.unbind(null,null,this);
        }
        order.bind('all',function(){
            self.order_changes();
        });
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

        // The exact amount must be paid if there is no cash payment method defined.
        if (Math.abs(order.get_total_with_tax() - order.get_total_paid()) > 0.00001) {
            var cash = false;
            for (var i = 0; i < this.pos.cashregisters.length; i++) {
                cash = cash || (this.pos.cashregisters[i].journal.type === 'cash');
            }
            if (!cash) {
                this.gui.show_popup('error',{
                    title: _t('Cannot return change without a cash payment method'),
                    body:  _t('There is no cash payment method available in this point of sale to handle the change.\n\n Please pay the exact amount or add a cash payment method in the point of sale configuration'),
                });
                return false;
            }
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

        if ((order.is_paid_with_cash() || order.get_change()) && this.pos.config.iface_cashdrawer) { 

                this.pos.proxy.open_cashbox();
        }

        order.initialize_validation_date();
        order.finalized = true;

        if (order.is_to_invoice()) {
            var invoiced = this.pos.push_and_invoice_order(order);
            this.invoicing = true;

            invoiced.fail(this._handleFailedPushForInvoice.bind(this, order, false));

            invoiced.done(function(){
                self.invoicing = false;
                self.gui.show_screen('receipt');
            });
        } else {
            this.pos.push_order(order);
            this.gui.show_screen('receipt');
        }

    },

    // Check if the order is paid, then sends it to the backend,
    // and complete the sale process
    validate_order: function(force_validation) {
        if (this.order_is_valid(force_validation)) {
            this.finalize_validation();
        }
    },
});
gui.define_screen({name:'payment', widget: PaymentScreenWidget});

var set_fiscal_position_button = ActionButtonWidget.extend({
    template: 'SetFiscalPositionButton',
    init: function (parent, options) {
        this._super(parent, options);

        this.pos.get('orders').bind('add remove change', function () {
            this.renderElement();
        }, this);

        this.pos.bind('change:selectedOrder', function () {
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
            title: _t('Select tax'),
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

        this.pos.get('orders').bind('add remove change', function () {
            this.renderElement();
        }, this);

        this.pos.bind('change:selectedOrder', function () {
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
        return this.pos.pricelists.length > 1;
    },
});

return {
    ReceiptScreenWidget: ReceiptScreenWidget,
    ActionButtonWidget: ActionButtonWidget,
    define_action_button: define_action_button,
    ScreenWidget: ScreenWidget,
    PaymentScreenWidget: PaymentScreenWidget,
    OrderWidget: OrderWidget,
    NumpadWidget: NumpadWidget,
    ProductScreenWidget: ProductScreenWidget,
    ProductListWidget: ProductListWidget,
    ClientListScreenWidget: ClientListScreenWidget,
    ActionpadWidget: ActionpadWidget,
    DomCache: DomCache,
    ProductCategoriesWidget: ProductCategoriesWidget,
    ScaleScreenWidget: ScaleScreenWidget,
    set_fiscal_position_button: set_fiscal_position_button,
    set_pricelist_button: set_pricelist_button,
};

});
