odoo.define('point_of_sale.chrome', function (require) {
"use strict";

var PosBaseWidget = require('point_of_sale.BaseWidget');
var gui = require('point_of_sale.gui');
var models = require('point_of_sale.models');
var core = require('web.core');
var ajax = require('web.ajax');
var CrashManager = require('web.CrashManager').CrashManager;
var BarcodeEvents = require('barcodes.BarcodeEvents').BarcodeEvents;

const { PosComponent } = require('point_of_sale.PosComponent');
const { useListener } = require('web.custom_hooks');

var _t = core._t;
var QWeb = core.qweb;

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
                    self.pos.set_synch('connected', 0);
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
                self.pos.proxy.test_ownership_of_client_screen().then(
                    function (data) {
                        if (typeof data === 'string') {
                            data = JSON.parse(data);
                        }
                        if (data.status === 'OWNER') {
                            self.change_status_display('success');
                        } else {
                            self.change_status_display('warning');
                        }
                        setTimeout(loop, 3000);
                    },
                    function (err) {
                        if (err.abort) {
                            // Stop the loop
                            return;
                        }
                        if (typeof err == "undefined") {
                            self.change_status_display('failure');
                        } else {
                            self.change_status_display('not_found');
                            self.pos.proxy.posbox_supports_display = false;
                        }
                        setTimeout(loop, 3000);
                    }
                );
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

class Chrome extends PosComponent {
    constructor() {
        super(...arguments);
        useListener('show-popup', this.__showPopup);
        useListener('close-popup', this.__closePopup);
        useListener('show-screen', this.showScreen);
        useListener('pos-error', this.onPosError);
        useListener('toggle-debug-widget', this.onToggleDebugWidget);
        this.$ = $;

        this.ready    = new $.Deferred(); // resolves when the whole GUI has been loaded
        this.webClient = this.props.webClient;

        // Instead of passing chrome to the instantiation the PosModel,
        // we inject functions needed by pos.
        // This way, we somehow decoupled Chrome from PosModel.
        // We can then test PosModel independently from Chrome by supplying
        // mocked version of these default attributes.
        const posModelDefaultAttributes = {
            rpc: this.rpc.bind(this),
            session: this.env.session,
            do_action: this.webClient.do_action.bind(this.webClient),
            loading_message: this.loading_message.bind(this),
            loading_skip: this.loading_skip.bind(this),
            loading_progress: this.loading_progress.bind(this),
        };

        this.pos = new models.PosModel(posModelDefaultAttributes);
        this.state = owl.useState({
            isReady: false,
            isShowDebugWidget: true,
            screen: this.getDefaultScreen(),
            popup: { isShow: false, name: null, component: null, props: {} },
        });
        this.chrome = this; // So that chrome's childs have chrome set automatically

        this.logo_click_time  = 0;
        this.logo_click_count = 0;

        this.previous_touch_y_coordinate = -1;

        this.widget = {};   // contains references to subwidgets instances
        this.widgets = [
        ];

        this.cleanup_dom();
    }

    __showPopup(event) {
        const { name, props, __theOneThatWaits } = event.detail;
        this.state.popup.isShow = true;
        this.state.popup.name = name;
        this.state.popup.component = this.constructor.components[name];
        this.state.popup.props = { ...props, __theOneThatWaits };
    }

    __closePopup() {
        this.state.popup.isShow = false;
    }

    mounted() {
        // We want the loading of pos models to be done when this root component
        // is already mounted. This way, we are able to use the state of this component
        // to rerender changes in the app.
        (async () => {
            try {
                await this.pos.ready;
                this.env.pos = this.pos;
                this.build_chrome();
                this.gui = new gui.Gui({pos: this.pos, chrome: this});
                this.pos.gui = this.gui;
                this.disable_rubberbanding();
                this.disable_backpace_back();
                await this.ready.resolve();
                this.loading_hide();
                this.replace_crashmanager();
                this.state.isReady = true;
                this.trigger('show-screen', { name: 'ProductScreen' })
                await this.pos.push_order();
                // await this.build_widgets();
            } catch (error) {
                this.loading_error(error)
            }
        })();
    }

    showScreen({ detail: { name, props } }) {
        this.state.screen.name = name;
        this.state.screen.component = this.constructor.components[name];
        this.state.screen.props = props || {};
    }

    /**
     * This is the generic function the handles the rendering error and triggerred
     * `pos-error` events.
     *
     * @param {Object} error
     */
    catchError(error) {
        if (this.isReady) {
            if (error instanceof Error) {
                this.showPopup('ErrorTracebackPopup', { title: error.message, body: error.stack });
            } else {
                this.showPopup('ErrorPopup', { title: error.message });
            }
        } else {
            console.error(error);
        }
    }

    /**
     * This is responsible on catching error outside the rendering context
     * of owl. What we do is trigger a `pos-error` event in the place where
     * we caught an error.
     *
     * @param {Event} event
     */
    onPosError(event) {
        const { error } = event.detail
        this.catchError(error);
    }

    cleanup_dom() {
        // remove default webclient handlers that induce click delay
        $(document).off();
        $(window).off();
        $('html').off();
        $('body').off();
        // The above lines removed the bindings, but we really need them for the barcode
        BarcodeEvents.start();
    }

    build_chrome() {
        var self = this;

        if ($.browser.chrome) {
            var chrome_version = $.browser.version.split('.')[0];
            if (parseInt(chrome_version, 10) >= 50) {
                ajax.loadCSS('/point_of_sale/static/src/css/chrome50.css');
            }
        }

        if(this.pos.config.iface_big_scrollbars){
            this.$el.addClass('big-scrollbars');
        }
    }

    // displays a system error with the error-traceback
    // popup.
    show_error(error) {
        this.showPopup('ErrorTracebackPopup',{
            'title': error.message,
            'body':  error.message + '\n' + error.data.debug + '\n',
        });
    }

    // replaces the error handling of the existing crashmanager which
    // uses jquery dialog to display the error, to use the pos popup
    // instead
    replace_crashmanager() {
        var self = this;
        CrashManager.include({
            show_error: function(error) {
                if (self.env.pos) {
                    self.show_error(error);
                } else {
                    this._super(error);
                }
            },
        });
    }

    onToggleDebugWidget() {
        this.state.isShowDebugWidget = !this.state.isShowDebugWidget;
    }

    _scrollable(element, scrolling_down){
        var $element = $(element);
        var scrollable = true;

        if (! scrolling_down && $element.scrollTop() <= 0) {
            scrollable = false;
        } else if (scrolling_down && $element.scrollTop() + $element.height() >= element.scrollHeight) {
            scrollable = false;
        }

        return scrollable;
    }

    disable_rubberbanding(){
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
    }

    // prevent backspace from performing a 'back' navigation
    disable_backpace_back() {
       $(document).on("keydown", function (e) {
           if (e.which === 8 && !$(e.target).is("input, textarea")) {
               e.preventDefault();
           }
       });
    }

    loading_error(err){
        var self = this;

        if (err.popup) {
            self.gui.show_popup('alert', {
                title: err.title,
                body: err.body,
            });
            return;
        }

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
    }
    loading_progress(fac){
        this.$('.loader .loader-feedback').removeClass('oe_hidden');
        this.$('.loader .progress').removeClass('oe_hidden').css({'width': ''+Math.floor(fac*100)+'%'});
    }
    loading_message(msg, progress) {
        this.$('.loader .loader-feedback').removeClass('oe_hidden');
        this.$('.loader .message').text(msg);
        if (typeof progress !== 'undefined') {
            this.loading_progress(progress);
        } else {
            this.$('.loader .progress').addClass('oe_hidden');
        }
    }
    loading_skip(callback){
        if(callback){
            this.$('.loader .loader-feedback').removeClass('oe_hidden');
            this.$('.loader .button.skip').removeClass('oe_hidden');
            this.$('.loader .button.skip').off('click');
            this.$('.loader .button.skip').click(callback);
        }else{
            this.$('.loader .button.skip').addClass('oe_hidden');
        }
    }
    loading_hide(){
        var self = this;
        this.$('.loader').animate({opacity:0},1500,'swing',function(){self.$('.loader').addClass('oe_hidden');});
    }
    loading_show(){
        this.$('.loader').removeClass('oe_hidden').animate({opacity:1},150,'swing');
    }

    destroy() {
        super.destroy(...arguments);
        this.pos.destroy();
    }

    getDefaultScreen() {
        const name = 'ProductScreen';
        const component = this.constructor.components[name];
        const props = {};
        return { name, component, props };
    }
}

return {
    Chrome: Chrome,
    DebugWidget: DebugWidget,
    ClientScreenWidget: ClientScreenWidget,
};
});
