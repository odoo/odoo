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

var ajax = require('web.ajax');
var Dialog = require('web.Dialog');
var website = require('website.website');

    var payment_methods = $('#payment_tokens_list');

    payment_methods.find('button[name="delete_pm_id"]').on('click', function(ev){
        ev.stopPropagation();
        ev.preventDefault();
        var self = this;

        // we retrieve the selected payment method id
        var payment_method_id = ev.target.value;

        var Delete = function()
        {
            payment_methods.find('button[name="delete_pm_id"]').off("click");
            ev.target.click();
        };

        ajax.jsonRpc('/website_payment/get_linked_records', 'call', {
            'payment_token_id': payment_method_id,
        }).done(function (response) {
            // if there's records linked to the payment method we're trying to delete
            if(response.length > 0)
            {
                var content = '';

                response.forEach(function(sub) {
                    content += '<p><a href="/my/subscription/' + sub.id + '">' + sub.name + '</a><p/>';
                });

                content = $('<div>').html('<p>This card is currently linked to the following records:<p/>' + content);
                // Then we display the list of the records and ask the user if he really want to remove the ppayment method.
                new Dialog(self, {
                    title: 'Warning!',
                    size: 'medium',
                    $content: content,
                    buttons: [
                    {text: 'Confirm Deletion', classes: 'btn-primary', close: true, click: Delete},
                    {text: 'Cancel', close: true}]}).open();
            }
            // otherwise if the user has no records linked to this payment method, then we just delete it.
            else
            {
                Delete();
            }
        });
    });
});
