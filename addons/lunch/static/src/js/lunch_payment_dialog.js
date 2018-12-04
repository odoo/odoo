odoo.define('lunch.LunchPaymentDialog', function (require) {
"use strict";

var core = require('web.core');
var Dialog = require('web.Dialog');

var qweb = core.qweb;

var LunchPaymentDialog = Dialog.extend({
    template: 'lunch.LunchPaymentDialog',

    init: function (parent, options) {
        var self = this;
        this._super.apply(this, arguments);

        options = (options || {});

        this.message = options.message || '';
    },
});

return LunchPaymentDialog;

});
