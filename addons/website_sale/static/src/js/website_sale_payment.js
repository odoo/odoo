odoo.define('website_sale.payment', function (require) {
"use strict";

var ajax = require('web.ajax');

$(document).ready(function () {
    // If option is enable
    if ($("#checkbox_cgv").length) {
      $("#checkbox_cgv").click(function() {
        $("div.oe_sale_acquirer_button").find('input, button').prop("disabled", !this.checked);
      });
    }

    // When choosing an acquirer, display its Pay Now button
    var $payment = $("#payment_method");
    $payment.on("click", "input[name='acquirer']", function (ev) {
            var payment_id = $(ev.currentTarget).val();
            $("div.oe_sale_acquirer_button[data-id]", $payment).addClass("hidden");
            $("div.oe_sale_acquirer_button[data-id='"+payment_id+"']", $payment).removeClass("hidden");
        })
        .find("input[name='acquirer']:checked").click();

    // When clicking on payment button: create the tx using json then continue to the acquirer
    $payment.on("click", 'button[type="submit"],button[name="submit"]', function (ev) {
      ev.preventDefault();
      ev.stopPropagation();
      var $form = $(ev.currentTarget).parents('form');
      var acquirer_id = $(ev.currentTarget).parents('div.oe_sale_acquirer_button').first().data('id');
      if (! acquirer_id) {
        return false;
      }
      ajax.jsonRpc('/shop/payment/transaction/' + acquirer_id, 'call', {}).then(function () {
        $form.submit();
      });
   });

});

});
