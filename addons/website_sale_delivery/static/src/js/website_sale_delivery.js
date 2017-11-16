$(document).ready(function () {

    var $pay_button = $('.oe_sale_acquirer_button button');
    $pay_button.prop('disabled', false);

    // When choosing an delivery carrier, update the quotation and the acquirers. Disable the 'Pay
    // Now' button to avoid being redirected to payment acquier if the delivery carrier update is
    // not over.
    var $carrier = $("#delivery_carrier");
    $carrier.find("input[name='delivery_type']").click(function (ev) {
        $pay_button.prop('disabled', true);
        var carrier_id = $(ev.currentTarget).val();
        window.location.href = '/shop/payment?carrier_id=' + carrier_id;
    });

    $(".oe_website_sale select[name='shipping_id']").on('change', function () {
        var value = $(this).val();
        var $provider_free = $("select[name='country_id']:not(.o_provider_restricted), select[name='state_id']:not(.o_provider_restricted)");
        var $provider_restricted = $("select[name='country_id'].o_provider_restricted, select[name='state_id'].o_provider_restricted");
        if (value == 0) {
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
