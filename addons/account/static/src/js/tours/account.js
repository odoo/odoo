odoo.define('account.tour', function(require) {
"use strict";

var core = require('web.core');
var tour = require('web_tour.tour');

var _t = core._t;

tour.register('account_tour', {
    'skip_enabled': true,
}, [{
    trigger: ".o_form_readonly .o_invoice_validate",
    extra_trigger: '.o_invoice_form',
    content: _t("Click to <b>validate your invoice.</b> A reference will be assigned to this invoice and you will not be able to modify it anymore."),
    position: "right"
}, {
    trigger: ".o_invoice_send",
    extra_trigger: '.o_invoice_form',
    content: _t("Click to <b>send the invoice by email.</b>"),
    position: "bottom"
}, {
    trigger: ".o_mail_send",
    content: _t("Click to <b>send the invoice.</b>"),
    position: "bottom"
} ]);

});
