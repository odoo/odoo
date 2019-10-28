odoo.define('pos_restaurant_hr.screens', function (require) {
    "use strict";

var ScreenWidget = require('point_of_sale.screens').ScreenWidget;

ScreenWidget.include({
    _get_floor_idle_exclude_screens: function(){
        return this._super().concat(['login-screen']);
    },
    _get_floor_idle_timeout: function() {
        if (this.pos.config.module_pos_hr && this.autolock && this.pos.config.auto_lock !== 0) {
            return (this.pos.config.auto_lock * 60000) - 10;
        }
        return this._super();
    },
    set_idle_timer: function(deactivate) {
        this._super(deactivate);
        if (!deactivate && this.pos.config.module_pos_hr && this.autolock && this.pos.config.auto_lock !== 0) {
            this.set_lock_timer();
        }
    },
});
})
