odoo.define('iap.redirect_odoo_credit_widget', function(require) {
"use strict";

var core = require('web.core');
var framework = require('web.framework');
var Widget = require('web.Widget');
var QWeb = core.qweb;


var IapOdooCreditRedirect = Widget.extend({
    template: 'iap.redirect_to_odoo_credit',
    events : {
        "click .redirect_confirm" : "odoo_redirect",
    },
    init: function (parent, action) {
        this._super(parent, action);
        this.url = action.params.url;
    },

    odoo_redirect: function () {
        window.open(this.url, '_blank');
        this.do_action({type: 'ir.actions.act_window_close'});
        // framework.redirect(this.url);
    },

});
core.action_registry.add('iap_odoo_credit_redirect', IapOdooCreditRedirect);
});
