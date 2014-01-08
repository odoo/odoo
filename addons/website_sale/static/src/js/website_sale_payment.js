$(document).ready(function () {

    // When choosing an acquirer, display its Pay Now button
    var $payment = $("#payment_method");
    $payment.find("input[name='acquirer']").click(function (ev) {
        var payment_id = $(ev.currentTarget).val();
        $("div.oe_sale_acquirer_button[data-id]", $payment).addClass("hidden");
        $("div.oe_sale_acquirer_button[data-id='"+payment_id+"']", $payment).removeClass("hidden");
    });

});
