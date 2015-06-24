$(document).ready(function () {

    // When choosing an delivery carrier, update the quotation and the acquirers
    var $carrier = $("#delivery_carrier");
    $carrier.find("input[name='delivery_type']").click(function (ev) {
        var carrier_id = $(ev.currentTarget).val();
        window.location.href = '/shop/payment?carrier_id=' + carrier_id;
    });

    $("select[name='shipping_id']").on('change', function () {
        var value = $(this).val();
        var $country_all = $(".js_country_all");
        var $country_snipping = $(".js_country_shipping");
        if (value == 0) {
            $country_all.hide().attr('disabled', true);
            $country_snipping.show().attr('disabled', false).change();
        } else {
            $country_all.show().attr('disabled', false).change();
            $country_snipping.hide().attr('disabled', true);
        }
    });

});
