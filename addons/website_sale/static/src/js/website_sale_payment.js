odoo.define('website_sale.payment', function (require) {
'use strict';

require('web.dom_ready');

var $checkbox = $("#checkbox_cgv");
if (!$checkbox.length) {
    return;
}

$checkbox.on('change', function (ev) {
    $('button#o_payment_form_pay').prop('disabled', !ev.target.checked);
});
$checkbox.change();
});
