odoo.define('website_payment.website_payment_card', function (require) {
"use strict";

var _t = require('web.core')._t;

$(document).ready(function () {

    $('input#cc_number').payment('formatCardNumber');
    $('input#cc_cvc').payment('formatCardCVC');
    $('input#cc_expiry').payment('formatCardExpiry')

    var valid_cc_number = false;
    var valid_cc_cvc = false;
    var valid_cc_expiry = false;

    $('input#cc_number').on('focusout', function (e) {
        valid_cc_number = $.payment.validateCardNumber(this.value);
        var card_type = $.payment.cardType(this.value);
        if (card_type) {
            $(this).parent('.form-group').children('.card_placeholder').removeClass().addClass('card_placeholder ' + card_type);
            $(this).parent('.form-group').children('input[name="cc_brand"]').val(card_type)
        }
        else {
            $(this).parent('.form-group').children('.card_placeholder').removeClass().addClass('card_placeholder');
        }
        if (valid_cc_number) {
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
        valid_cc_cvc = $.payment.validateCardCVC(this.value, card_type);
        if (valid_cc_cvc) {
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
        valid_cc_expiry = $.payment.validateCardExpiry(month, year);
        if (valid_cc_expiry) {
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

    $('#delete_payment_method').on('show.bs.modal', function(e){
        var pm_method_id = $(e.relatedTarget).data('pm_id')
        $(e.target).find('input[name="delete_pm_id"]').val(pm_method_id)
    });

    $('#add_payment_method').on('click', '.btn-payment-submit', function (event){
        event.preventDefault();
        var $form = $(this).closest('form');

        if (valid_cc_number && valid_cc_cvc && valid_cc_expiry){
            $form.submit();
        }
        else {
            $('#add_payment_method').find('.card_detail').remove();
            $form.prepend($('<div>',{
                class: 'alert alert-danger card_detail',
                text:  _t('Please insert valid card detail!')
                })
            )
        }
    });
});
});
