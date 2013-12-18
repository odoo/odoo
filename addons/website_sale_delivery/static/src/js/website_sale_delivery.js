$(document).ready(function () {

    // When choosing an delivery carrier, update the quotation and the acquirers
    var $carrier = $("#delivery_carrier");
    $carrier.find("input[name='delivery_type']").click(function (ev) {
        var carrier_id = $(ev.currentTarget).val();
        var link = $carrier.find('a');
        link.attr('href', '/shop/payment?carrier_id=' + carrier_id);
        window.location.href = link.attr('href');
    });

});
