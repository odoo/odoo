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
    $payment.on("click", "input[name='acquirer'], button.btn_payment_token", function (ev) {
            var payment_id = $(ev.currentTarget).val() || $(this).data('acquirer');
            $("div.oe_sale_acquirer_button[data-id]", $payment).addClass("hidden");
            $("div.oe_sale_acquirer_button[data-id='"+payment_id+"']", $payment).removeClass("hidden");

            // show token
            $("div.list-group[data-acquirer!='"+payment_id+"']", $payment).hide();
            $("div.list-group[data-acquirer='"+payment_id+"']", $payment).show();

            var token = $(ev.currentTarget).data('token') || '';
            $("div.oe_sale_acquirer_button[data-id='"+payment_id+"']", $payment).attr('data-token', token);

        })
        .find("input[name='acquirer']:checked").click();

    // When clicking on payment button: create the tx using json then continue to the acquirer
    $payment.on("click", 'button[type="submit"], button[name="submit"]', function (ev) {
      ev.preventDefault();
      ev.stopPropagation();
      var $form = $(ev.currentTarget).parents('form');
      var acquirer = $(ev.currentTarget).parents('div.oe_sale_acquirer_button').first();
      var acquirer_id = acquirer.data('id');
      var acquirer_token = acquirer.attr('data-token'); // !=data
      var params = {};
      if (! acquirer_id) {
        return false;
      }
      if (acquirer_token) {
        params.token = acquirer_token;
      }
      $form.off('submit');
      ajax.jsonRpc('/shop/payment/transaction/' + acquirer_id, 'call', params).then(function (data) {
          $(data).submit();
      });
      return false;
    });

    $('div.oe_pay_token').on('click', 'a.js_btn_valid_tx', function() {
      $('div.js_token_load').toggle();

      var $form = $(this).parents('form');
      ajax.jsonRpc($form.attr('action'), 'call', $.deparam($form.serialize())).then(function (data) {
        if (data.url) {
          window.location = data.url;
        }
        else {
          $('div.js_token_load').toggle();
          if (!data.success && data.error) {
            $('div.oe_pay_token div.panel-body p').html(data.error + "<br/><br/>" + _('Retry ? '));
            $('div.oe_pay_token div.panel-body').parents('div').removeClass('panel-info').addClass('panel-danger');
          }
        }
      });

    });

});

});
