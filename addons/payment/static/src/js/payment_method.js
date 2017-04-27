odoo.define('payment.payment_method', function (require) {
"use strict";

    var ajax = require('web.ajax');
    var Widget = require('web.Widget');

    var PaymentMethod = Widget.extend({
        events: {
            'click input[name="acquirer"], a.btn_payment_token': 'pay_now',
            'click button[type="submit"], button[name="submit"]': 'payment_transaction',
        },

        start: function() {
            this._super.apply(this, arguments);
            this.$("input[name='acquirer']:checked").click();
        },

        pay_now: function(event){
            var self = this,
                ico_off = 'fa-circle-o',
                ico_on = 'fa-dot-circle-o';

            var $acquirer_el = $(event.currentTarget),
                payment_id = $acquirer_el.val() || $acquirer_el.data('acquirer'),
                token = $acquirer_el.data('token') || '';

            self.$('div.js_payment a.list-group-item').removeClass("list-group-item-info");
            self.$('span.js_radio').switchClass(ico_on, ico_off, 0);

            if (token) {
                self.$('div.o_acquirer_button[data-id=' +payment_id+ ']').attr('data-token', token);
                self.$('div.o_acquirer_button div.token_hide').hide();
                $acquirer_el.find('span.js_radio').switchClass(ico_off, ico_on, 0);
                $acquirer_el.parents('li').find('input').prop("checked", true);
                $acquirer_el.addClass("list-group-item-info");
            } else {
                self.$("div.o_acquirer_button div.token_hide").show();
            }
            self.$('div.o_acquirer_button[data-id]').addClass("hidden");
            self.$('div.o_acquirer_button[data-id=' +payment_id+ ']').removeClass("hidden");
        },

        payment_transaction: function(event){
            event.preventDefault();
            event.stopPropagation();

            var self = this,
                $acquirer_el = $(event.currentTarget),
                $form = $acquirer_el.parents('form'),
                acquirer = $acquirer_el.parents('div.o_acquirer_button').first(),
                acquirer_id = acquirer.data('id'),
                acquirer_token = acquirer.attr('data-token'); // !=data

            var params = {'tx_type': acquirer.find('input[name="odoo_save_token"]').is(':checked')?'form_save':'form'};
            if (! acquirer_id) {
                return false;
            }
            if (acquirer_token) {
                params.token = acquirer_token;
            }
            $form.off('submit');
            self.payment_transaction_action(acquirer_id, params);
        },

        payment_transaction_action: function(acquirer_id, params){
            // override this function as per controllers(route) of module wise
            return false;
        },
    });

    $(document).ready(function (){
        $('div.o_pay_token').on('click', 'a.js_btn_valid_tx', function() {
            $('div.js_token_load').toggle();
            var $form = $(this).parents('form');
            ajax.jsonRpc($form.attr('action'), 'call', $.deparam($form.serialize())).then(function (data) {
                if (data.url) {
                    window.location = data.url;
                }
                else {
                    $('div.js_token_load').toggle();
                    if (!data.success && data.error) {
                        $('div.o_pay_token div.panel-body p').html(data.error + "<br/><br/>" + _('Retry ? '));
                        $('div.o_pay_token div.panel-body').parents('div').removeClass('panel-info').addClass('panel-danger');
                    }
                }
            });
        });
    });
    return PaymentMethod;
});
