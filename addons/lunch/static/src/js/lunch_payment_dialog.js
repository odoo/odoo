odoo.define('lunch.LunchPaymentDialog', function (require) {
"use strict";

var Dialog = require('web.Dialog');

var LunchPaymentDialog = Dialog.extend({
    template: 'lunch.LunchPaymentDialog',

    init: function (parent, options) {
        this._super.apply(this, arguments);

        options = options || {};

        this.message = options.message || '';
    },
});

return LunchPaymentDialog;

});
