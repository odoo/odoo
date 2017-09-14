odoo.define('website_sale_delivery.website_sale_delivery', function (require) {
'use strict';

    require('web.dom_ready');
    var ajax = require('web.ajax');

    if (!$('.oe_website_sale').length) {
        return $.Deferred().reject("DOM doesn't contain '.oe_website_sale'");
    }

    // When choosing an delivery carrier, update the quotation and the acquirers.
    var $carrier = $("#delivery_carrier");
    $carrier.find("input[name='delivery_type']").click(function (ev) {
        $(ev.currentTarget).prop('checked', false);
        $(ev.currentTarget).closest('.o_website_sale_delivery_method_panel').click();
    });

    $carrier.find(".o_website_sale_delivery_method_panel").click(function (ev) {
        var $elem = $(ev.currentTarget);
        var $radio = $elem.find("input:radio")
        if (!$radio.is(':checked')) {
            $carrier.find('input:radio').prop('checked', false);
            $radio.prop('checked', true);
            $radio.next().append("<i class='fa fa-spinner fa-spin ml4 o_website_sale_apply_carrier'></i>");
            var carrier_id = $elem.data('delivery-id');
            ajax.jsonRpc("/shop/" + carrier_id + "/delivery_carrier", 'call')
            .done(function (data) {
                $('.o_website_sale_amount_tax .oe_currency_value').text(data.amount_tax.toFixed(2));
                $('.o_website_sale_amount_untaxed .oe_currency_value').text(data.amount_untaxed.toFixed(2));
                $('.o_website_sale_amount_total .oe_currency_value').text(data.amount_total.toFixed(2));
                $('.o_website_sale_delivery_error_message').remove();
                if (data && data.delivery_rating_success) {
                    $('.o_website_sale_order_delivery').removeClass('hidden');
                    $('.o_website_sale_amount_delivery .oe_currency_value').text(data.delivery_price.toFixed(2));
                    $elem.find('.o_website_sale_compute_delivery_price').addClass('hidden').prev('.o_website_sale_delivery_price').removeClass('hidden').find('.oe_currency_value').text(data.delivery_price.toFixed(2));
                } else {
                    data.delivery_message[0] = "<h4>" + data.delivery_message[0] + "</h4>";
                    $('.oe_cart').prepend("<div class='alert alert-danger o_website_sale_delivery_error_message'>" + data.delivery_message.join(' ') + "</div>");
                    $('.o_website_sale_order_delivery').addClass('hidden');
                    $('body').scrollTop(0);
                }
                $elem.find('.o_website_sale_apply_carrier').remove();
            });
            return false;
        }
    });

    $carrier.find(".o_website_sale_compute_delivery_price").click(function (ev) {
        ev.stopPropagation();
        var $computeButton = $(ev.currentTarget);
        $computeButton.prepend("<i class='fa fa-spinner fa-spin mr4'/>");
        var carrier_id = $computeButton.data('delivery-id');
        ajax.jsonRpc("/shop/" + carrier_id + "/delivery_price", 'call')
        .done(function (data) {
            if ('price' in data) {
                $computeButton.prev('.o_website_sale_delivery_price').removeClass('hidden').find('.oe_currency_value').text(data.price.toFixed(2));
                $computeButton.remove();
            } else {
                $computeButton.parent().html('<div class="alert alert-danger alert-dismissible text-left" role="alert" onclick="event.stopPropagation()">' +
                    '<a class="close" data-dismiss="alert" aria-label="close" onclick="event.target.parentNode.remove()">x</a>' +
                    data.error_message + '</div>');
            }
        });
    });

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
