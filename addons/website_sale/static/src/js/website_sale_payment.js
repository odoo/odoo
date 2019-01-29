odoo.define('website_sale.payment', function (require) {
'use strict';

require('web.dom_ready');

var $checkbox = $("#checkbox_cgv");
if (!$checkbox.length) {
    return;
}
var $pay_button = $('button#o_payment_form_pay');

$checkbox.on('change', function (ev) {
    $pay_button.data('disabled_reasons', $pay_button.data('disabled_reasons') || {});
    $pay_button.data('disabled_reasons').cgv = !ev.target.checked;
    $pay_button.prop('disabled', _.contains($pay_button.data('disabled_reasons'), true));
});
$checkbox.change();
});
