odoo.define('point_of_sale.chrome', function (require) {
"use strict";

var gui = require('point_of_sale.gui');
var models = require('point_of_sale.models');
var core = require('web.core');
var ajax = require('web.ajax');
var CrashManager = require('web.CrashManager').CrashManager;
var BarcodeEvents = require('barcodes.BarcodeEvents').BarcodeEvents;

const { useState } = owl;
const { PosComponent } = require('point_of_sale.PosComponent');
const { useListener } = require('web.custom_hooks');

var _t = core._t;
var QWeb = core.qweb;

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
        useListener('show-screen', this.showScreen);
        useListener('pos-error', this.onPosError);
        useListener('toggle-debug-widget', this.onToggleDebugWidget);
        useListener('show-popup', this.__showPopup);
        useListener('close-popup', this.__closePopup);
        useListener('show-temp-screen', this.__showTempScreen);
        useListener('close-temp-screen', this.__closeTempScreen);
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
        // states
        this.state = useState({
            isReady: false,
            isShowDebugWidget: true,
        });
        this.mainScreen = useState(this._getDefaultScreen())
        this.mainScreenProps = {};
        this.popup = useState({ isShow: false, name: null, component: null });
        this.popupProps = {}; // We want to avoid making the props to become Proxy!
        this.tempScreen = useState({ isShow: false, name: null, component: null});
        this.tempScreenProps = {};

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
        const { name, props, resolve, numberBuffer } = event.detail;
        this.popup.isShow = true;
        this.popup.name = name;
        this.popup.component = this.constructor.components[name];
        this.popupProps = { ...props, resolve, numberBuffer };
        if (numberBuffer) {
            numberBuffer.pause();
        }
    }

    __closePopup() {
        this.popup.isShow = false;
        if (this.popupProps.numberBuffer) {
            this.popupProps.numberBuffer.resume();
        }
    }

    get isShowClientScreenButton() {
        return this.env.pos.config.use_proxy && this.env.pos.config.iface_customer_facing_display;
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

    __showTempScreen(event) {
        const { name, props, resolve, numberBuffer } = event.detail;
        this.tempScreen.isShow = true;
        this.tempScreen.name = name;
        this.tempScreen.component = this.constructor.components[name];
        this.tempScreenProps = { ...props, resolve, numberBuffer };
        // hide main screen
        this.mainScreen.isShow = false;
        // pause numberBuffer
        if (numberBuffer) {
            numberBuffer.pause();
        }
    }

    __closeTempScreen() {
        this.tempScreen.isShow = false;
        // show main screen
        this.mainScreen.isShow = true;
        // resume numberBuffer
        if (this.tempScreenProps.numberBuffer) {
            this.tempScreenProps.numberBuffer.resume();
        }
    }

    showScreen({ detail: { name, props } }) {
        this.mainScreen.isShow = true;
        this.mainScreen.name = name;
        this.mainScreen.component = this.constructor.components[name];
        this.mainScreenProps = props || {};
    }

    /**
     * This is the generic function the handles the rendering error and triggerred
     * `pos-error` events.
     *
     * @param {Object} error
     */
    catchError(error) {
        if (this.state.isReady) {
            if (error instanceof Error) {
                this.showPopup('ErrorTracebackPopup', { title: error.message, body: error.stack });
            } else {
                this.showPopup('ErrorPopup', { title: error.message });
            }
        }
        console.error(error);
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
            'title': error.type,
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

    _getDefaultScreen() {
        const name = 'ProductScreen';
        const component = this.constructor.components[name];
        return { name, component };
    }
}

return { Chrome };
});
