odoo.define('pos_hr.screens', function (require) {
    "use strict";

var core = require('web.core');
var gui = require('point_of_sale.gui');
var ScreenWidget = require('point_of_sale.screens').ScreenWidget;

var _t = core._t;

ScreenWidget.include({
    autolock: true,

    // what happens when a cashier id barcode is scanned.
    // the default behavior is the following : 
    // - if there's an employee with a matching barcode, put it as the active 'cashier', go to cashier mode, and return true
    // - else : do nothing and return false. You probably want to extend this to show and appropriate error popup... 
    barcode_cashier_action: function(code){
        var self = this;
        var employees = this.pos.employees;
        var prom;
        for(var i = 0, len = employees.length; i < len; i++){
            if(employees[i].barcode === Sha1.hash(code.code)){
                if (employees[i].id !== this.pos.get_cashier().id && employees[i].pin) {
                    prom =  this.gui.ask_password(employees[i].pin).then(function(){
                        self.pos.set_cashier(employees[i]);
                        self.chrome.widget.username.renderElement();
                        return true;
                    });
                } else {
                    this.pos.set_cashier(employees[i]);
                    this.chrome.widget.username.renderElement();
                    prom = Promise.resolve(true);
                }
                break;
            }
        }
        if (!prom){
            this.barcode_error_action(code);
            return Promise.resolve(false);
        }
        else {
            return prom
        }
    },
    renderElement: function() {
        this._super();
        console.log('setting lock '+ this.$el.attr('class'));
        if (this.pos.config.module_pos_hr) {
            this.pos.barcode_reader.set_action_callback('cashier', _.bind(this.barcode_cashier_action, this));
            
            if (this.autolock && this.pos.config.auto_lock !== 0) {
                if (!this.$el.hasClass('login-screen')){
                    var self = this;
                    console.log('set lock '+ this.$el.attr('class'));
                    this.$el.on(
                            'mousemove mousedown touchstart click scroll keypress',
                            function() {self.set_lock_timer()}
                    );
                }
            }
        }
    },
    show: function() {
        this._super();
        if (this.pos.config.module_pos_hr && this.autolock && this.pos.config.auto_lock !== 0) {
            this.set_lock_timer();
        }
    },
    close: function() {
        this._super();
        this.set_lock_timer(true);
    },
    set_lock_timer: function(deactivate) {
        var timeout = this.pos.config.auto_lock * 60000;
        deactivate = deactivate || false;
        if (this.lock_timer) {
            clearTimeout(this.lock_timer);
        }
        if (!deactivate  && !this.hidden) {
            var self = this;
            this.lock_timer = setTimeout(function(){
                self.gui.show_screen('login');
            }, timeout);
        }
    },
});

/*--------------------------------------*\
 |         THE LOGIN SCREEN           |
\*======================================*/

// The login screen enables employees to log in to the PoS
// at startup or after it was locked, with either barcode, pin, or both.

var LoginScreenWidget = ScreenWidget.extend({
    template: 'LoginScreenWidget',
    autolock: false,

    /**
     * @override
     */
    show: function() {
        var self = this;
        this.$('.select-employee').click(function() {
            self.gui.select_employee({
                'security': true,
                'current_employee': self.pos.get_cashier(),
                'title':_t('Change Cashier'),})
            .then(function(employee){
                self.pos.set_cashier(employee);
                self.chrome.widget.username.renderElement();
                self.unlock_screen();
            });
        });
        this._super();
    },

    /**
     * @override
     */
    barcode_cashier_action: function(code) {
        var self = this;
        return this._super(code).then(function () {
            self.unlock_screen();
        });
    },

    unlock_screen: function() {
        var screen = (this.gui.pos.get_order() ? this.gui.pos.get_order().get_screen_data('previous-screen') : this.gui.startup_screen) || this.gui.startup_screen;
        this.gui.show_screen(screen);
    }
});

gui.define_screen({name:'login', widget: LoginScreenWidget});

return {
    LoginScreenWidget: LoginScreenWidget
};
});
