odoo.define('pos_hr.gui', function (require) {
    "use strict";

var core = require('web.core');
var gui = require('point_of_sale.gui');
var _t = core._t;

gui.Gui.include({
    _show_first_screen: function () {
        if (this.pos.config.module_pos_hr) {
            this.show_screen('login');
        } else {
            this._super();
        }
    },
    show_screen: function(screen_name, params, refresh, skip_close_popup){
        var order = this.pos.get_order();
        if (order) {
            if (screen_name === 'login') {
                order.set_screen_data( 'screen' ,[
                        order.get_screen_data('previous-screen'), 
                        this.get_current_screen()
                ]);
            } else if (Array.isArray(order.get_screen_data('previous-screen'))) {
                order.set_screen_data('screen', order.get_screen_data('previous-screen')[0]);
                screen_name = order.get_screen_data('previous-screen')[1];
            }
        }
        this._super(screen_name, params, refresh, skip_close_popup);
    },
    select_employee: function(options) {
        options = options || {};
        var self = this;

        var list = [];
        this.pos.employees.forEach(function(employee) {
            if (!options.only_managers || employee.role === 'manager') {
                list.push({
                'label': employee.name,
                'item':  employee,
                });
            }
        });

        var prom = new Promise(function (resolve, reject) {
            self.show_popup('selection', {
                title: options.title || _t('Select User'),
                list: list,
                confirm: resolve,
                cancel: reject,
                is_selected: function (employee) {
                    return employee === self.pos.get_cashier();
                },
            });
        });

        return prom.then(function (employee) {
            return self.ask_password(employee.pin).then(function(){
                return employee;
            });
        });
    },
    // Ask for a password, and checks if it this
    // the same as specified by the function call.
    // Returns a promise that resolves on success,
    // fails on failure.
    ask_password: function(password) {
        var self = this;
        var prom = new Promise(function (resolve, reject) {
            if (password) {
                self.show_popup('password',{
                    'title': _t('Password ?'),
                    confirm: function (pw) {
                        if (Sha1.hash(pw) !== password) {
                            self.show_popup('error', _t('Incorrect Password'));
                            reject();
                        } else {
                            resolve();
                        }
                    },
                });
            } else {
                resolve();
            }
        });
        return prom;
    },
});
});
