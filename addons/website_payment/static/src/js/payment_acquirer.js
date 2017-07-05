$(document).ready(function () {

    $('input#cc_number').payment('formatCardNumber');
    $('input#cc_cvc').payment('formatCardCVC');
    $('input#cc_expiry').payment('formatCardExpiry')

    $('input#cc_number').on('focusout', function (e) {
        var valid_value = $.payment.validateCardNumber(this.value);
        var card_type = $.payment.cardType(this.value);
        if (card_type) {
            $(this).parent('.form-group').children('.card_placeholder').removeClass().addClass('card_placeholder ' + card_type);
            $(this).parent('.form-group').children('input[name="cc_brand"]').val(card_type)
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
        if (valid_value) {
            $(this).parent('.form-group').addClass('has-success');
            $(this).parent('.form-group').removeClass('has-error');
        }
        else {
            $(this).parent('.form-group').addClass('has-error');
            $(this).parent('.form-group').removeClass('has-success');
        }
    });

    $('select[name="pm_acquirer_id"]').on('change', function() {
        var acquirer_id = $(this).val();
        $('.acquirer').addClass('hidden');
        $('.acquirer[data-acquirer-id="'+acquirer_id+'"]').removeClass('hidden');
    });

});


odoo.define('website_payment.payment_acquirer', function (require) {
"use strict";

var website = require('website.website');
var ajax = require('web.ajax');
var Dialog = require('web.Dialog');

    var payment_methods = $('table#payment_methods');

    payment_methods.find('form').find('button[type="submit"]').on('click', function(ev){
        ev.stopPropagation();
        ev.preventDefault();

        var Delete = function()
        {
            ev.currentTarget.parentElement.submit();
        }

        var content = $('<div>').html("<p>Be aware that if this credit card is linked to an ongoing contract, <b>it will prevent the payment of it.</b></p>" + 
        "<p>Are you sure you want to proceed?</p>");
        new Dialog(this, {
            title: 'Warning!',
            size: 'medium',
            $content: content,
            buttons: [
            {text: 'Delete', classes: 'btn-primary', close: true, click: Delete},
            {text: 'Cancel', close: true}]}).open();

    });


});