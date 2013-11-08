$(document).ready(function () {

    $('input#cc_number').payment('formatCardNumber');
    $('input#cc_cvc').payment('formatCardCVC');
    $('input#cc_expiry_mm').payment('restrictNumeric');
    $('input#cc_expiry_yy').payment('restrictNumeric');

    $('input#cc_number').on('focusout', function (e) {
        var valid_value = $.payment.validateCardNumber(this.value);
        console.log('check: ', valid_value);
    });
});
