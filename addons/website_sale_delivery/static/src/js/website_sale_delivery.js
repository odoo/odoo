'use strict';
odoo.define('website_sale_delivery.checkout', function (require) {

    require('web.dom_ready');
    var ajax = require('web.ajax');

    /* Handle interactive carrier choice + cart update */
    var $pay_button = $('#o_payment_form_pay');

    var _onCarrierUpdateAnswer = function(result) {
        var $amount_delivery = $('#order_delivery span.oe_currency_value');
        var $amount_untaxed = $('#order_total_untaxed span.oe_currency_value');
        var $amount_tax = $('#order_total_taxes span.oe_currency_value');
        var $carrier_badge = $('#delivery_carrier input[name="delivery_type"][value=' + result.carrier_id + '] ~ .badge.hidden');
        var $compute_badge = $('#delivery_carrier input[name="delivery_type"][value=' + result.carrier_id + '] ~ .o_delivery_compute');
        if (result.status === true) {
            $amount_delivery.text(result.new_amount_delivery);
            $amount_untaxed.text(result.new_amount_untaxed);
            $amount_tax.text(result.new_amount_tax);
            $carrier_badge.children('span').text(result.new_amount_delivery);
            $carrier_badge.removeClass('hidden');
            $compute_badge.addClass('hidden');
            $pay_button.prop('disabled', false);
        }
        else {
            console.error(result.error_message);
            $compute_badge.text(result.error_message);
        }
    };

    var _onCarrierClick = function(ev) {
        $pay_button.prop('disabled', true);
        var carrier_id = $(ev.currentTarget).val();
        var values = {'carrier_id': carrier_id};
        ajax.jsonRpc('/shop/update_carrier', 'call', values)
          .then(_onCarrierUpdateAnswer);
    };

    var $carriers = $("#delivery_carrier input[name='delivery_type']");
    $carriers.click(_onCarrierClick);

    /* Handle stuff */
    $(".oe_website_sale select[name='shipping_id']").on('change', function () {
        var value = $(this).val();
        var $provider_free = $("select[name='country_id']:not(.o_provider_restricted), select[name='state_id']:not(.o_provider_restricted)");
        var $provider_restricted = $("select[name='country_id'].o_provider_restricted, select[name='state_id'].o_provider_restricted");
        if (value === 0) {
            // Ship to the same address : only show shipping countries available for billing
            $provider_free.hide().attr('disabled', true);
            $provider_restricted.show().attr('disabled', false).change();
        } else {
            // Create a new address : show all countries available for billing
            $provider_free.show().attr('disabled', false).change();
            $provider_restricted.hide().attr('disabled', true);
        }
    });

});
