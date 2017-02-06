odoo.define('point_of_sale.gui', function (require) {
"use strict";
// this file contains the Gui, which is the pos 'controller'. 
// It contains high level methods to manipulate the interface
// such as changing between screens, creating popups, etc.
//
// it is available to all pos objects trough the '.gui' field.

var core = require('web.core');
var Model = require('web.DataModel');
var formats = require('web.formats');
var session = require('web.session');

var _t = core._t;

var Gui = core.Class.extend({
    screen_classes: [],
    popup_classes:  [],
    init: function(options){
        var self = this;
        this.pos            = options.pos;
        this.chrome         = options.chrome;
        this.screen_instances     = {};
        this.popup_instances      = {};
        this.default_screen = null;
        this.startup_screen = null;
        this.current_popup  = null;
        this.current_screen = null; 

        this.chrome.ready.then(function(){
            self.close_other_tabs();
            var order = self.pos.get_order();
            if (order) {
                self.show_saved_screen(order);
            } else {
                self.show_screen(self.startup_screen);
            }
            self.pos.bind('change:selectedOrder', function(){
                self.show_saved_screen(self.pos.get_order());
            });
        });
    },

    /* ---- Gui: SCREEN MANIPULATION ---- */

    // register a screen widget to the gui,
    // it must have been inserted into the dom.
    add_screen: function(name, screen){
        screen.hide();
        this.screen_instances[name] = screen;
    },

    // sets the screen that will be displayed
    // for new orders
    set_default_screen: function(name){ 
        this.default_screen = name;
    },

    // sets the screen that will be displayed
    // when no orders are present
    set_startup_screen: function(name) {
        this.startup_screen = name;
    },

    // display the screen saved in an order,
    // called when the user changes the current order
    // no screen saved ? -> display default_screen
    // no order ? -> display startup_screen
    show_saved_screen:  function(order,options) {
        options = options || {};
        this.close_popup();
        if (order) {
            this.show_screen(order.get_screen_data('screen') || 
                             options.default_screen || 
                             this.default_screen,
                             null,'refresh');
        } else {
            this.show_screen(this.startup_screen);
        }
    },

    // display a screen. 
    // If there is an order, the screen will be saved in the order
    // - params: used to load a screen with parameters, for
    // example loading a 'product_details' screen for a specific product.
    // - refresh: if you want the screen to cycle trough show / hide even
    // if you are already on the same screen.
    show_screen: function(screen_name,params,refresh) {
        var screen = this.screen_instances[screen_name];
        if (!screen) {
            console.error("ERROR: show_screen("+screen_name+") : screen not found");
        }

        this.close_popup();

        var order = this.pos.get_order();
        if (order) {
            var old_screen_name = order.get_screen_data('screen');

            order.set_screen_data('screen',screen_name);

            if(params){
                order.set_screen_data('params',params);
            }

            if( screen_name !== old_screen_name ){
                order.set_screen_data('previous-screen',old_screen_name);
            }
        }

        if (refresh || screen !== this.current_screen) {
            if (this.current_screen) {
                this.current_screen.close();
                this.current_screen.hide();
            }
            this.current_screen = screen;
            this.current_screen.show(refresh);
        }
    },
    
    // returns the current screen.
    get_current_screen: function() {
        return this.pos.get_order() ? ( this.pos.get_order().get_screen_data('screen') || this.default_screen ) : this.startup_screen;
    },

    // goes to the previous screen (as specified in the order). The history only
    // goes 1 deep ...
    back: function() {
        var previous = this.pos.get_order().get_screen_data('previous-screen');
        if (previous) {
            this.show_screen(previous);
        }
    },

    // returns the parameter specified when this screen was displayed
    get_current_screen_param: function(param) {
        if (this.pos.get_order()) {
            var params = this.pos.get_order().get_screen_data('params');
            return params ? params[param] : undefined;
        } else {
            return undefined;
        }
    },

    /* ---- Gui: POPUP MANIPULATION ---- */

    // registers a new popup in the GUI.
    // the popup must have been previously inserted
    // into the dom.
    add_popup: function(name, popup) {
        popup.hide();
        this.popup_instances[name] = popup;
    },

    // displays a popup. Popup do not stack,
    // are not remembered by the order, and are
    // closed by screen changes or new popups.
    show_popup: function(name,options) {
        if (this.current_popup) {
            this.close_popup();
        }
        this.current_popup = this.popup_instances[name];
        return this.current_popup.show(options);
    },

    // close the current popup.
    close_popup: function() {
        if  (this.current_popup) {
            this.current_popup.close();
            this.current_popup.hide();
            this.current_popup = null;
        }
    },

    // is there an active popup ?
    has_popup: function() {
        return !!this.current_popup;
    },

    /* ---- Gui: INTER TAB COMM ---- */

    // This sets up automatic pos exit when open in
    // another tab.
    close_other_tabs: function() {
        var self = this;

        localStorage['message'] = '';
        localStorage['message'] = JSON.stringify({
            'message':'close_tabs',
            'session': this.pos.pos_session.id,
        });

        window.addEventListener("storage", function(event) {
            var msg = event.data;

            if ( event.key === 'message' && event.newValue) {

                var msg = JSON.parse(event.newValue);
                if ( msg.message  === 'close_tabs' &&
                     msg.session  ==  self.pos.pos_session.id ) {

                    console.info('POS / Session opened in another window. EXITING POS')
                    self._close();
                }
            }

        }, false);
    },

    /* ---- Gui: ACCESS CONTROL ---- */

    // A Generic UI that allow to select a user from a list.
    // It returns a deferred that resolves with the selected user 
    // upon success. Several options are available :
    // - security: passwords will be asked
    // - only_managers: restricts the list to managers
    // - current_user: password will not be asked if this 
    //                 user is selected.
    // - title: The title of the user selection list. 
    select_user: function(options){
        options = options || {};
        var self = this;
        var def  = new $.Deferred();

        var list = [];
        for (var i = 0; i < this.pos.users.length; i++) {
            var user = this.pos.users[i];
            if (!options.only_managers || user.role === 'manager') {
                list.push({
                    'label': user.name,
                    'item':  user,
                });
            }
        }

        this.show_popup('selection',{
            'title': options.title || _t('Select User'),
            list: list,
            confirm: function(user){ def.resolve(user); },
            cancel:  function(){ def.reject(); },
        });

        return def.then(function(user){
            if (options.security && user !== options.current_user && user.pos_security_pin) {
                return self.ask_password(user.pos_security_pin).then(function(){
                    return user;
                });
            } else {
                return user;
            }
        });
    },

    // Ask for a password, and checks if it this
    // the same as specified by the function call.
    // returns a deferred that resolves on success,
    // fails on failure.
    ask_password: function(password) {
        var self = this;
        var ret = new $.Deferred();
        if (password) {
            this.show_popup('password',{
                'title': _t('Password ?'),
                confirm: function(pw) {
                    if (pw !== password) {
                        self.show_popup('error',_t('Incorrect Password'));
                        ret.reject();
                    } else {
                        ret.resolve();
                    }
                },
            });
        } else {
            ret.resolve();
        }
        return ret;
    },

    // checks if the current user (or the user provided) has manager
    // access rights. If not, a popup is shown allowing the user to
    // temporarily login as an administrator. 
    // This method returns a deferred, that succeeds with the 
    // manager user when the login is successfull.
    sudo: function(user){
        user = user || this.pos.get_cashier();

        if (user.role === 'manager') {
            return new $.Deferred().resolve(user);
        } else {
            return this.select_user({
                security:       true, 
                only_managers:  true,
                title:       _t('Login as a Manager'),
            });
        }
    },

    /* ---- Gui: CLOSING THE POINT OF SALE ---- */

    close: function() {
        var self = this;
        var pending = this.pos.db.get_orders().length;

        if (!pending) {
            this._close();
        } else {
            this.pos.push_order().always(function() {
                var pending = self.pos.db.get_orders().length;
                if (!pending) {
                    self._close();
                } else {
                    var reason = self.pos.get('failed') ? 
                                 'configuration errors' : 
                                 'internet connection issues';  

                    self.show_popup('confirm', {
                        'title': _t('Offline Orders'),
                        'body':  _t(['Some orders could not be submitted to',
                                     'the server due to ' + reason + '.',
                                     'You can exit the Point of Sale, but do',
                                     'not close the session before the issue',
                                     'has been resolved.'].join(' ')),
                        'confirm': function() {
                            self._close();
                        },
                    });
                }
            });
        }
    },

    _close: function() {
        var self = this;
        this.chrome.loading_show();
        this.chrome.loading_message(_t('Closing ...'));

        this.pos.push_order().then(function(){
            var url = "/web#action=point_of_sale.action_client_pos_menu";
            window.location = session.debug ? $.param.querystring(url, {debug: session.debug}) : url;
        });
    },

    /* ---- Gui: SOUND ---- */

    play_sound: function(sound) {
        var src = '';
        if (sound === 'error') {
            src = "/point_of_sale/static/src/sounds/error.wav";
        } else if (sound === 'bell') {
            src = "/point_of_sale/static/src/sounds/bell.wav";
        } else {
            console.error('Unknown sound: ',sound);
            return;
        }
        $('body').append('<audio src="'+src+'" autoplay="true"></audio>');
    },

    /* ---- Gui: FILE I/O ---- */

    // This will make the browser download 'contents' as a 
    // file named 'name'
    // if 'contents' is not a string, it is converted into
    // a JSON representation of the contents. 


    // TODO: remove me in master: deprecated in favor of prepare_download_link
    // this method is kept for backward compatibility but is likely not going
    // to work as many browsers do to not accept fake click events on links
    download_file: function(contents, name) {
        href_params = this.prepare_file_blob(contents,name);
        var evt  = document.createEvent("HTMLEvents");
        evt.initEvent("click");

        $("<a>",href_params).get(0).dispatchEvent(evt);
        
    },      
    
    prepare_download_link: function(contents, filename, src, target) {
        var href_params = this.prepare_file_blob(contents, filename);

        $(target).parent().attr(href_params);
        $(src).addClass('oe_hidden');
        $(target).removeClass('oe_hidden');

        // hide again after click
        $(target).click(function() {
            $(src).removeClass('oe_hidden');
            $(this).addClass('oe_hidden');
        });
    },  
    
    prepare_file_blob: function(contents, name) {
        var URL = window.URL || window.webkitURL;
        
        if (typeof contents !== 'string') {
            contents = JSON.stringify(contents,null,2);
        }

        var blob = new Blob([contents]);

        return {download: name || 'document.txt',
                href: URL.createObjectURL(blob),}
    },

    /* ---- Gui: EMAILS ---- */

    // This will launch the user's email software
    // with a new email with the address, subject and body
    // prefilled.

    send_email: function(address, subject, body) {
        window.open("mailto:" + address + 
                          "?subject=" + (subject ? window.encodeURIComponent(subject) : '') +
                          "&body=" + (body ? window.encodeURIComponent(body) : ''));
    },

    /* ---- Gui: KEYBOARD INPUT ---- */

    // This is a helper to handle numpad keyboard input. 
    // - buffer: an empty or number string
    // - input:  '[0-9],'+','-','.','CLEAR','BACKSPACE'
    // - options: 'firstinput' -> will clear buffer if
    //     input is '[0-9]' or '.'
    //  returns the new buffer containing the modifications
    //  (the original is not touched) 
    numpad_input: function(buffer, input, options) { 
        var newbuf  = buffer.slice(0);
        options = options || {};
        var newbuf_float  = formats.parse_value(newbuf, {type: "float"}, 0);
        var decimal_point = _t.database.parameters.decimal_point;

        if (input === decimal_point) {
            if (options.firstinput) {
                newbuf = "0.";
            }else if (!newbuf.length || newbuf === '-') {
                newbuf += "0.";
            } else if (newbuf.indexOf(decimal_point) < 0){
                newbuf = newbuf + decimal_point;
            }
        } else if (input === 'CLEAR') {
            newbuf = ""; 
        } else if (input === 'BACKSPACE') { 
            newbuf = newbuf.substring(0,newbuf.length - 1);
        } else if (input === '+') {
            if ( newbuf[0] === '-' ) {
                newbuf = newbuf.substring(1,newbuf.length);
            }
        } else if (input === '-') {
            if ( newbuf[0] === '-' ) {
                newbuf = newbuf.substring(1,newbuf.length);
            } else {
                newbuf = '-' + newbuf;
            }
        } else if (input[0] === '+' && !isNaN(parseFloat(input))) {
            newbuf = this.chrome.format_currency_no_symbol(newbuf_float + parseFloat(input));
        } else if (!isNaN(parseInt(input))) {
            if (options.firstinput) {
                newbuf = '' + input;
            } else {
                newbuf += input;
            }
        }

        // End of input buffer at 12 characters.
        if (newbuf.length > buffer.length && newbuf.length > 12) {
            this.play_sound('bell');
            return buffer.slice(0);
        }

        return newbuf;
    },
});

var define_screen = function (classe) {
    Gui.prototype.screen_classes.push(classe);
};

var define_popup = function (classe) {
    Gui.prototype.popup_classes.push(classe);
};

return {
    Gui: Gui,
    define_screen: define_screen,
    define_popup: define_popup,
};

});
