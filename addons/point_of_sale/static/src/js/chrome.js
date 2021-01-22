odoo.define('point_of_sale.chrome', function (require) {
"use strict";

var PosBaseWidget = require('point_of_sale.BaseWidget');
var gui = require('point_of_sale.gui');
var keyboard = require('point_of_sale.keyboard');
var models = require('point_of_sale.models');
var AbstractAction = require('web.AbstractAction');
var core = require('web.core');
var ajax = require('web.ajax');
var CrashManager = require('web.CrashManager');
var BarcodeEvents = require('barcodes.BarcodeEvents').BarcodeEvents;


var _t = core._t;
var _lt = core._lt;
var QWeb = core.qweb;

/* -------- The Order Selector -------- */

// Allows the cashier to create / delete and
// switch between orders.

var OrderSelectorWidget = PosBaseWidget.extend({
    template: 'OrderSelectorWidget',
    init: function(parent, options) {
        this._super(parent, options);
        this.pos.get('orders').bind('add remove change',this.renderElement,this);
        this.pos.bind('change:selectedOrder',this.renderElement,this);
    },
    get_order_by_uid: function(uid) {
        var orders = this.pos.get_order_list();
        for (var i = 0; i < orders.length; i++) {
            if (orders[i].uid === uid) {
                return orders[i];
            }
        }
        return undefined;
    },
    order_click_handler: function(event,$el) {
        var order = this.get_order_by_uid($el.data('uid'));
        if (order) {
            this.pos.set_order(order);
        }
    },
    neworder_click_handler: function(event, $el) {
        this.pos.add_new_order();
    },
    deleteorder_click_handler: function(event, $el) {
        var self  = this;
        var order = this.pos.get_order(); 
        if (!order) {
            return;
        } else if ( !order.is_empty() ){
            this.gui.show_popup('confirm',{
                'title': _t('Destroy Current Order ?'),
                'body': _t('You will lose any data associated with the current order'),
                confirm: function(){
                    self.pos.delete_current_order();
                },
            });
        } else {
            this.pos.delete_current_order();
        }
    },
    renderElement: function(){
        var self = this;
        this._super();
        this.$('.order-button.select-order').click(function(event){
            self.order_click_handler(event,$(this));
        });
        this.$('.neworder-button').click(function(event){
            self.neworder_click_handler(event,$(this));
        });
        this.$('.deleteorder-button').click(function(event){
            self.deleteorder_click_handler(event,$(this));
        });
    },
});

/* ------- The User Name Widget ------- */

// Displays the current cashier's name and allows
// to switch between cashiers.

var UsernameWidget = PosBaseWidget.extend({
    template: 'UsernameWidget',
    init: function(parent, options){
        options = options || {};
        this._super(parent,options);
    },
    renderElement: function(){
        var self = this;
        this._super();

        this.$el.click(function(){
            self.click_username();
        });
    },
    click_username: function(){
        var self = this;
        this.gui.select_user({
            'security':     true,
            'current_user': this.pos.get_cashier(),
            'title':      _t('Change Cashier'),
        }).then(function(user){
            self.pos.set_cashier(user);
            self.renderElement();
        });
    },
    get_name: function(){
        var user = this.pos.get_cashier();
        if(user){
            return user.name;
        }else{
            return "";
        }
    },
});

/* -------- The Header Button --------- */

// Used to quickly add buttons with simple
// labels and actions to the point of sale 
// header.

var HeaderButtonWidget = PosBaseWidget.extend({
    template: 'HeaderButtonWidget',
    init: function(parent, options){
        options = options || {};
        this._super(parent, options);
        this.action = options.action;
        this.label   = options.label;
    },
    renderElement: function(){
        var self = this;
        this._super();
        if(this.action){
            this.$el.click(function(){
                self.action();
            });
        }
    },
    show: function(){ this.$el.removeClass('oe_hidden'); },
    hide: function(){ this.$el.addClass('oe_hidden'); },
});

/* --------- The Debug Widget --------- */

// The debug widget lets the user control 
// and monitor the hardware and software status
// without the use of the proxy, or to access
// the raw locally stored db values, useful
// for debugging

var DebugWidget = PosBaseWidget.extend({
    template: "DebugWidget",
    eans:{
        admin_badge:  '0410100000006',
        client_badge: '0420200000004',
        invalid_ean:  '1232456',
        soda_33cl:    '5449000000996',
        oranges_kg:   '2100002031410',
        lemon_price:  '2301000001560',
        unknown_product: '9900000000004',
    },
    events:[
        'open_cashbox',
        'print_receipt',
        'scale_read',
    ],
    init: function(parent,options){
        this._super(parent,options);
        var self = this;
        
        // for dragging the debug widget around
        this.dragging  = false;
        this.dragpos = {x:0, y:0};

        function eventpos(event){
            if(event.touches && event.touches[0]){
                return {x: event.touches[0].screenX, y: event.touches[0].screenY};
            }else{
                return {x: event.screenX, y: event.screenY};
            }
        }

        this.dragend_handler = function(event){
            self.dragging = false;
        };
        this.dragstart_handler = function(event){
            self.dragging = true;
            self.dragpos = eventpos(event);
        };
        this.dragmove_handler = function(event){
            if(self.dragging){
                var top = this.offsetTop;
                var left = this.offsetLeft;
                var pos  = eventpos(event);
                var dx   = pos.x - self.dragpos.x; 
                var dy   = pos.y - self.dragpos.y; 

                self.dragpos = pos;

                this.style.right = 'auto';
                this.style.bottom = 'auto';
                this.style.left = left + dx + 'px';
                this.style.top  = top  + dy + 'px';
            }
            event.preventDefault();
            event.stopPropagation();
        };
    },
    show: function() {
        this.$el.css({opacity:0});
        this.$el.removeClass('oe_hidden');
        this.$el.animate({opacity:1},250,'swing');
    },
    hide: function() {
        var self = this;
        this.$el.animate({opacity:0,},250,'swing',function(){
            self.$el.addClass('oe_hidden');
        });
    },
    start: function(){
        var self = this;
        
        if (this.pos.debug) {
            this.show();
        }

        this.el.addEventListener('mouseleave', this.dragend_handler);
        this.el.addEventListener('mouseup',    this.dragend_handler);
        this.el.addEventListener('touchend',   this.dragend_handler);
        this.el.addEventListener('touchcancel',this.dragend_handler);
        this.el.addEventListener('mousedown',  this.dragstart_handler);
        this.el.addEventListener('touchstart', this.dragstart_handler);
        this.el.addEventListener('mousemove',  this.dragmove_handler);
        this.el.addEventListener('touchmove',  this.dragmove_handler);

        this.$('.toggle').click(function(){
            self.hide();
        });
        this.$('.button.set_weight').click(function(){
            var kg = Number(self.$('input.weight').val());
            if(!isNaN(kg)){
                self.pos.proxy.debug_set_weight(kg);
            }
        });
        this.$('.button.reset_weight').click(function(){
            self.$('input.weight').val('');
            self.pos.proxy.debug_reset_weight();
        });
        this.$('.button.custom_ean').click(function(){
            var ean = self.pos.barcode_reader.barcode_parser.sanitize_ean(self.$('input.ean').val() || '0');
            self.$('input.ean').val(ean);
            self.pos.barcode_reader.scan(ean);
        });
        this.$('.button.barcode').click(function(){
            self.pos.barcode_reader.scan(self.$('input.ean').val());
        });
        this.$('.button.delete_orders').click(function(){
            self.gui.show_popup('confirm',{
                'title': _t('Delete Paid Orders ?'),
                'body':  _t('This operation will permanently destroy all paid orders from the local storage. You will lose all the data. This operation cannot be undone.'),
                confirm: function(){
                    self.pos.db.remove_all_orders();
                    self.pos.set({synch: { state:'connected', pending: 0 }});
                },
            });
        });
        this.$('.button.delete_unpaid_orders').click(function(){
            self.gui.show_popup('confirm',{
                'title': _t('Delete Unpaid Orders ?'),
                'body':  _t('This operation will destroy all unpaid orders in the browser. You will lose all the unsaved data and exit the point of sale. This operation cannot be undone.'),
                confirm: function(){
                    self.pos.db.remove_all_unpaid_orders();
                    window.location = '/';
                },
            });
        });

        this.$('.button.export_unpaid_orders').click(function(){
            self.gui.prepare_download_link(
                self.pos.export_unpaid_orders(),
                _t("unpaid orders") + ' ' + moment().format('YYYY-MM-DD-HH-mm-ss') + '.json',
                ".export_unpaid_orders", ".download_unpaid_orders"
            );
        });

        this.$('.button.export_paid_orders').click(function() {
            self.gui.prepare_download_link(
                self.pos.export_paid_orders(),
                _t("paid orders") + ' ' + moment().format('YYYY-MM-DD-HH-mm-ss') + '.json',
                ".export_paid_orders", ".download_paid_orders"
            );
        });

        this.$('.button.display_refresh').click(function () {
            self.pos.proxy.message('display_refresh', {});
        });

        this.$('.button.import_orders input').on('change', function(event) {
            var file = event.target.files[0];

            if (file) {
                var reader = new FileReader();
                
                reader.onload = function(event) {
                    var report = self.pos.import_orders(event.target.result);
                    self.gui.show_popup('orderimport',{report:report});
                };
                
                reader.readAsText(file);
            }
        });

        _.each(this.events, function(name){
            self.pos.proxy.add_notification(name,function(){
                self.$('.event.'+name).stop().clearQueue().css({'background-color':'#6CD11D'}); 
                self.$('.event.'+name).animate({'background-color':'#1E1E1E'},2000);
            });
        });
    },
});

/* --------- The Status Widget -------- */

// Base class for widgets that want to display
// status in the point of sale header.

var StatusWidget = PosBaseWidget.extend({
    status: ['connected','connecting','disconnected','warning','error'],

    set_status: function(status,msg){
        for(var i = 0; i < this.status.length; i++){
            this.$('.js_'+this.status[i]).addClass('oe_hidden');
        }
        this.$('.js_'+status).removeClass('oe_hidden');
        
        if(msg){
            this.$('.js_msg').removeClass('oe_hidden').html(msg);
        }else{
            this.$('.js_msg').addClass('oe_hidden').html('');
        }
    },
});

/* ------- Synch. Notifications ------- */

// Displays if there are orders that could
// not be submitted, and how many. 

var SynchNotificationWidget = StatusWidget.extend({
    template: 'SynchNotificationWidget',
    start: function(){
        var self = this;
        this.pos.bind('change:synch', function(pos,synch){
            self.set_status(synch.state, synch.pending);
        });
        this.$el.click(function(){
            self.pos.push_order(null,{'show_error':true});
        });
    },
});

/* --------- The Proxy Status --------- */

// Displays the status of the hardware proxy
// (connected, disconnected, errors ... )

var ProxyStatusWidget = StatusWidget.extend({
    template: 'ProxyStatusWidget',
    set_smart_status: function(status){
        if(status.status === 'connected'){
            var warning = false;
            var msg = '';
            if(this.pos.config.iface_scan_via_proxy){
                var scanner = status.drivers.scanner ? status.drivers.scanner.status : false;
                if( scanner != 'connected' && scanner != 'connecting'){
                    warning = true;
                    msg += _t('Scanner');
                }
            }
            if( this.pos.config.iface_print_via_proxy || 
                this.pos.config.iface_cashdrawer ){
                var printer = status.drivers.escpos ? status.drivers.escpos.status : false;
                if( printer != 'connected' && printer != 'connecting'){
                    warning = true;
                    msg = msg ? msg + ' & ' : msg;
                    msg += _t('Printer');
                }
            }
            if( this.pos.config.iface_electronic_scale ){
                var scale = status.drivers.scale ? status.drivers.scale.status : false;
                if( scale != 'connected' && scale != 'connecting' ){
                    warning = true;
                    msg = msg ? msg + ' & ' : msg;
                    msg += _t('Scale');
                }
            }

            msg = msg ? msg + ' ' + _t('Offline') : msg;
            this.set_status(warning ? 'warning' : 'connected', msg);
        }else{
            this.set_status(status.status,'');
        }
    },
    start: function(){
        var self = this;
        
        this.set_smart_status(this.pos.proxy.get('status'));

        this.pos.proxy.on('change:status',this,function(eh,status){ //FIXME remove duplicate changes 
            self.set_smart_status(status.newValue);
        });

        this.$el.click(function(){
            self.pos.connect_to_proxy();
        });
    },
});


/* --------- The Sale Details --------- */

// Generates a report to print the sales of the
// day on a ticket

var SaleDetailsButton = PosBaseWidget.extend({
    template: 'SaleDetailsButton',
    start: function(){
        var self = this;
        this.$el.click(function(){
            self.pos.proxy.print_sale_details();
        });
    },
});

/* User interface for distant control over the Client display on the IoT Box */
// The boolean posbox_supports_display (in devices.js) will allow interaction to the IoT Box on true, prevents it otherwise
// We don't want the incompatible IoT Box to be flooded with 404 errors on arrival of our many requests as it triggers losses of connections altogether
var ClientScreenWidget = PosBaseWidget.extend({
    template: 'ClientScreenWidget',

    change_status_display: function(status) {
        var msg = ''
        if (status === 'success') {
            this.$('.js_warning').addClass('oe_hidden');
            this.$('.js_disconnected').addClass('oe_hidden');
            this.$('.js_connected').removeClass('oe_hidden');
        } else if (status === 'warning') {
            this.$('.js_disconnected').addClass('oe_hidden');
            this.$('.js_connected').addClass('oe_hidden');
            this.$('.js_warning').removeClass('oe_hidden');
            msg = _t('Connected, Not Owned');
        } else {
            this.$('.js_warning').addClass('oe_hidden');
            this.$('.js_connected').addClass('oe_hidden');
            this.$('.js_disconnected').removeClass('oe_hidden');
            msg = _t('Disconnected')
            if (status === 'not_found') {
                msg = _t('Client Screen Unsupported. Please upgrade the IoT Box')
            }
        }

        this.$('.oe_customer_display_text').text(msg);
    },

    status_loop: function() {
        var self = this;
        function loop() {
            if (self.pos.proxy.posbox_supports_display) {
                var deffered = self.pos.proxy.test_ownership_of_client_screen();
                if (deffered) {
                    deffered.then(
                        function(data) {
                            if (typeof data === 'string') {
                                data = JSON.parse(data);
                            }
                            if (data.status === 'OWNER') {
                                self.change_status_display('success');
                            } else {
                                self.change_status_display('warning');
                              }
                        },
                        
                        function(err) {
                            if (typeof err == "undefined") {
                                self.change_status_display('failure');
                            } else {
                                self.change_status_display('not_found');
                                self.pos.proxy.posbox_supports_display = false;
                            }
                        })
    
                    .always(function () {
                        setTimeout(loop,3000);
                    });
                }
            }   
        }
        loop();
    },

    start: function(){
        if (this.pos.config.iface_customer_facing_display) {
                this.show();
                var self = this;
                this.$el.click(function(){
                    self.pos.render_html_for_customer_facing_display().then(function(rendered_html) {
                        self.pos.proxy.take_ownership_over_client_screen(rendered_html).then(
       
                        function(data) {
                            if (typeof data === 'string') {
                                data = JSON.parse(data);
                            }
                            if (data.status === 'success') {
                               self.change_status_display('success');
                            } else {
                               self.change_status_display('warning');
                            }
                            if (!self.pos.proxy.posbox_supports_display) {
                                self.pos.proxy.posbox_supports_display = true;
                                self.status_loop();
                            }
                        }, 
        
                        function(err) {
                            if (typeof err == "undefined") {
                                self.change_status_display('failure');
                            } else {
                                self.change_status_display('not_found');
                            }
                        });
                    });

                });
                this.status_loop();
        } else {
            this.hide();
        }
    },
});


/*--------------------------------------*\
 |             THE CHROME               |
\*======================================*/

// The Chrome is the main widget that contains 
// all other widgets in the PointOfSale.
//
// It is the first object instanciated and the
// starting point of the point of sale code.
//
// It is mainly composed of :
// - a header, containing the list of orders
// - a leftpane, containing the list of bought 
//   products (orderlines) 
// - a rightpane, containing the screens 
//   (see pos_screens.js)
// - popups
// - an onscreen keyboard
// - .gui which controls the switching between 
//   screens and the showing/closing of popups

var Chrome = PosBaseWidget.extend(AbstractAction.prototype, {
    template: 'Chrome',
    init: function() { 
        var self = this;
        this._super(arguments[0],{});

        this.started  = new $.Deferred(); // resolves when DOM is online
        this.ready    = new $.Deferred(); // resolves when the whole GUI has been loaded

        this.pos = new models.PosModel(this.getSession(), {chrome:this});
        this.gui = new gui.Gui({pos: this.pos, chrome: this});
        this.chrome = this; // So that chrome's childs have chrome set automatically
        this.pos.gui = this.gui;

        this.logo_click_time  = 0;
        this.logo_click_count = 0;

            this.previous_touch_y_coordinate = -1;

        this.widget = {};   // contains references to subwidgets instances

        this.cleanup_dom();

        this.pos.ready.done(function(){
            self.build_chrome();
            self.build_widgets();
            self.disable_rubberbanding();
            self.disable_backpace_back();
            self.ready.resolve();
            self.loading_hide();
            self.replace_crashmanager();
            self.pos.push_order();
        }).fail(function(err){   // error when loading models data from the backend
            self.loading_error(err);
        });
    },

    cleanup_dom:  function() {
        // remove default webclient handlers that induce click delay
        $(document).off();
        $(window).off();
        $('html').off();
        $('body').off();
        // The above lines removed the bindings, but we really need them for the barcode
        BarcodeEvents.start();
    },

    build_chrome: function() { 
        var self = this;

        if ($.browser.chrome) {
            var chrome_version = $.browser.version.split('.')[0];
            if (parseInt(chrome_version, 10) >= 50) {
                ajax.loadCSS('/point_of_sale/static/src/css/chrome50.css');
            }
        }

        this.renderElement();

        this.$('.pos-logo').click(function(){
            self.click_logo();
        });

        if(this.pos.config.iface_big_scrollbars){
            this.$el.addClass('big-scrollbars');
        }
    },

    // displays a system error with the error-traceback
    // popup.
    show_error: function(error) {
        this.gui.show_popup('error-traceback',{
            'title': error.message,
            'body':  error.message + '\n' + error.data.debug + '\n',
        });
    },

    // replaces the error handling of the existing crashmanager which
    // uses jquery dialog to display the error, to use the pos popup
    // instead
    replace_crashmanager: function() {
        var self = this;
        CrashManager.include({
            show_error: function(error) {
                if (self.gui) {
                    self.show_error(error);
                } else {
                    this._super(error);
                }
            },
        });
    },

    click_logo: function() {
        if (this.pos.debug) {
            this.widget.debug.show();
        } else {
            var self  = this;
            var time  = (new Date()).getTime();
            var delay = 500;
            if (this.logo_click_time + 500 < time) {
                this.logo_click_time  = time;
                this.logo_click_count = 1;
            } else {
                this.logo_click_time  = time;
                this.logo_click_count += 1;
                if (this.logo_click_count >= 6) {
                    this.logo_click_count = 0;
                    this.gui.sudo().then(function(){
                        self.widget.debug.show();
                    });
                }
            }
        }
    },

        _scrollable: function(element, scrolling_down){
            var $element = $(element);
            var scrollable = true;

            if (! scrolling_down && $element.scrollTop() <= 0) {
                scrollable = false;
            } else if (scrolling_down && $element.scrollTop() + $element.height() >= element.scrollHeight) {
                scrollable = false;
            }

            return scrollable;
        },

    disable_rubberbanding: function(){
            var self = this;

            document.body.addEventListener('touchstart', function(event){
                self.previous_touch_y_coordinate = event.touches[0].clientY;
            });

        // prevent the pos body from being scrollable. 
        document.body.addEventListener('touchmove',function(event){
            var node = event.target;
                var current_touch_y_coordinate = event.touches[0].clientY;
                var scrolling_down;

                if (current_touch_y_coordinate < self.previous_touch_y_coordinate) {
                    scrolling_down = true;
                } else {
                    scrolling_down = false;
                }

            while(node){
                if(node.classList && node.classList.contains('touch-scrollable') && self._scrollable(node, scrolling_down)){
                    return;
                }
                node = node.parentNode;
            }
            event.preventDefault();
        });
    },

    // prevent backspace from performing a 'back' navigation
    disable_backpace_back: function() {
       $(document).on("keydown", function (e) {
           if (e.which === 8 && !$(e.target).is("input, textarea")) {
               e.preventDefault();
           }
       });
    },

    loading_error: function(err){
        var self = this;

        var title = err.message;
        var body  = err.stack;

        if(err.message === 'XmlHttpRequestError '){
            title = 'Network Failure (XmlHttpRequestError)';
            body  = 'The Point of Sale could not be loaded due to a network problem.\n Please check your internet connection.';
        }else if(err.code === 200){
            title = err.data.message;
            body  = err.data.debug;
        }

        if( typeof body !== 'string' ){
            body = 'Traceback not available.';
        }

        var popup = $(QWeb.render('ErrorTracebackPopupWidget',{
            widget: { options: {title: title , body: body }},
        }));

        popup.find('.button').click(function(){
            self.gui.close();
        });

        popup.css({ zindex: 9001 });

        popup.appendTo(this.$el);
    },
    loading_progress: function(fac){
        this.$('.loader .loader-feedback').removeClass('oe_hidden');
        this.$('.loader .progress').removeClass('oe_hidden').css({'width': ''+Math.floor(fac*100)+'%'});
    },
    loading_message: function(msg,progress){
        this.$('.loader .loader-feedback').removeClass('oe_hidden');
        this.$('.loader .message').text(msg);
        if (typeof progress !== 'undefined') {
            this.loading_progress(progress);
        } else {
            this.$('.loader .progress').addClass('oe_hidden');
        }
    },
    loading_skip: function(callback){
        if(callback){
            this.$('.loader .loader-feedback').removeClass('oe_hidden');
            this.$('.loader .button.skip').removeClass('oe_hidden');
            this.$('.loader .button.skip').off('click');
            this.$('.loader .button.skip').click(callback);
        }else{
            this.$('.loader .button.skip').addClass('oe_hidden');
        }
    },
    loading_hide: function(){
        var self = this;
        this.$('.loader').animate({opacity:0},1500,'swing',function(){self.$('.loader').addClass('oe_hidden');});
    },
    loading_show: function(){
        this.$('.loader').removeClass('oe_hidden').animate({opacity:1},150,'swing');
    },
    widgets: [
        {
            'name':   'order_selector',
            'widget': OrderSelectorWidget,
            'replace':  '.placeholder-OrderSelectorWidget',
        },{
            'name':   'sale_details',
            'widget': SaleDetailsButton,
            'append':  '.pos-rightheader',
            'condition': function(){ return this.pos.config.use_proxy; },
        },{
            'name':   'proxy_status',
            'widget': ProxyStatusWidget,
            'append':  '.pos-rightheader',
            'condition': function(){ return this.pos.config.use_proxy; },
        },{
            'name': 'screen_status',
            'widget': ClientScreenWidget,
            'append': '.pos-rightheader',
            'condition': function(){ return this.pos.config.use_proxy; },
        },{
            'name':   'notification',
            'widget': SynchNotificationWidget,
            'append':  '.pos-rightheader',
        },{
            'name':   'close_button',
            'widget': HeaderButtonWidget,
            'append':  '.pos-rightheader',
            'args': {
                label: _lt('Close'),
                action: function(){ 
                    var self = this;
                    if (!this.confirmed) {
                        this.$el.addClass('confirm');
                        this.$el.text(_t('Confirm'));
                        this.confirmed = setTimeout(function(){
                            self.$el.removeClass('confirm');
                            self.$el.text(_t('Close'));
                            self.confirmed = false;
                        },2000);
                    } else {
                        clearTimeout(this.confirmed);
                        this.$el.removeClass('confirm');
                        this.$el.text(_t('Close'));
                        this.confirmed = false;
                        this.gui.close();
                    }
                },
            }
        },{
            'name':   'username',
            'widget': UsernameWidget,
            'replace':  '.placeholder-UsernameWidget',
        },{
            'name':  'keyboard',
            'widget': keyboard.OnscreenKeyboardWidget,
            'replace': '.placeholder-OnscreenKeyboardWidget',
        },{
            'name':  'debug',
            'widget': DebugWidget,
            'append': '.pos-content',
        },
    ],

    // This method instantiates all the screens, widgets, etc. 
    build_widgets: function() {
        var classe;

        for (var i = 0; i < this.widgets.length; i++) {
            var def = this.widgets[i];
            if ( !def.condition || def.condition.call(this) ) {
                var args = typeof def.args === 'function' ? def.args(this) : def.args;
                var w = new def.widget(this, args || {});
                if (def.replace) {
                    w.replace(this.$(def.replace));
                } else if (def.append) {
                    w.appendTo(this.$(def.append));
                } else if (def.prepend) {
                    w.prependTo(this.$(def.prepend));
                } else {
                    w.appendTo(this.$el);
                }
                this.widget[def.name] = w;
            }
        }

        this.screens = {};
        for (i = 0; i < this.gui.screen_classes.length; i++) {
            classe = this.gui.screen_classes[i];
            if (!classe.condition || classe.condition.call(this)) {
                var screen = new classe.widget(this,{});
                    screen.appendTo(this.$('.screens'));
                this.screens[classe.name] = screen;
                this.gui.add_screen(classe.name, screen);
            }
        }

        this.popups = {};
        for (i = 0; i < this.gui.popup_classes.length; i++) {
            classe = this.gui.popup_classes[i];
            if (!classe.condition || classe.condition.call(this)) {
                var popup = new classe.widget(this,{});
                    popup.appendTo(this.$('.popups'));
                this.popups[classe.name] = popup;
                this.gui.add_popup(classe.name, popup);
            }
        }

        this.gui.set_startup_screen('products');
        this.gui.set_default_screen('products');

    },

    destroy: function() {
        this.pos.destroy();
        this._super();
    }
});

return {
    Chrome: Chrome,
    DebugWidget: DebugWidget,
    HeaderButtonWidget: HeaderButtonWidget,
    OrderSelectorWidget: OrderSelectorWidget,
    ProxyStatusWidget: ProxyStatusWidget,
    SaleDetailsButton: SaleDetailsButton,
    ClientScreenWidget: ClientScreenWidget,
    StatusWidget: StatusWidget,
    SynchNotificationWidget: SynchNotificationWidget,
    UsernameWidget: UsernameWidget,
};
});
