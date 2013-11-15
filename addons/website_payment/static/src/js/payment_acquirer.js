$(document).ready(function () {

    $('input#cc_number').payment('formatCardNumber');
    $('input#cc_cvc').payment('formatCardCVC');
    $('input#cc_expiry').payment('formatCardExpiry')

    $('input#cc_number').on('focusout', function (e) {
        var valid_value = $.payment.validateCardNumber(this.value);
        var card_type = $.payment.cardType(this.value);
        console.log('Validating card', this.value, 'is a', card_type, 'and valid:', valid_value);
        if (card_type) {
            $(this).parent('.form-group').children('.card_placeholder').removeClass().addClass('card_placeholder ' + card_type);
        }
        else {
            $(this).parent('.form-group').children('.card_placeholder').removeClass().addClass('card_placeholder');   
        }
        if (valid_value) {
            $(this).parent('.form-group').addClass('has-success');
            $(this).parent('.form-group').removeClass('has-error');
        }
        else {
            $(this).parent('.form-group').addClass('has-error');
            $(this).parent('.form-group').removeClass('has-success');
        }
    });

    $('input#cc_cvc').on('focusout', function (e) {
        var cc_nbr = $(this).parents('.oe_cc').find('#cc_number').val();
        var card_type = $.payment.cardType(cc_nbr);
        var valid_value = $.payment.validateCardCVC(this.value, card_type);
        console.log('Validating CVC', this.value, 'for card', cc_nbr, 'of type', card_type, 'and is valid:', valid_value);
        if (valid_value) {
            $(this).parent('.form-group').addClass('has-success');
            $(this).parent('.form-group').removeClass('has-error');
        }
        else {
            $(this).parent('.form-group').addClass('has-error');
            $(this).parent('.form-group').removeClass('has-success');
        }
    });

    $('input#cc_expiry').on('focusout', function (e) {
        var expiry_value = $.payment.cardExpiryVal(this.value);
        var month = expiry_value.month || '';
        var year = expiry_value.year || '';
        var valid_value = $.payment.validateCardExpiry(month, year);
        console.log('Validating expiry', this.value, 'month', month, 'year', year, 'and is valid:', valid_value);
        if (valid_value) {
            $(this).parent('.form-group').addClass('has-success');
            $(this).parent('.form-group').removeClass('has-error');
        }
        else {
            $(this).parent('.form-group').addClass('has-error');
            $(this).parent('.form-group').removeClass('has-success');
        }
    });

});
