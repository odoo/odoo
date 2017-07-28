odoo.define('payment.payment_form', function (require){
    "use strict";

    var ajax = require('web.ajax');
    var core = require('web.core');
    var Dialog = require("web.Dialog");
    var Widget = require("web.Widget");
    var rpc = require("web.rpc");
    var _t = core._t;

    var PaymentForm = Widget.extend({

        events: {
            'click #o_payment_form_pay': 'payEvent',
            'click #o_payment_form_add_pm': 'addPmEvent',
            'click button[name="delete_pm"]': 'deletePmEvent',
            'click input[type="radio"]': 'radioClickEvent'
        },

        payEvent: function(ev) {
            ev.stopPropagation();
            ev.preventDefault();
            var form = this.el;
            var checked_radio = this.$('input[type="radio"]:checked');
            var self = this;
            var button = ev.target;

            // first we check that the user has selected a payment method
            if(checked_radio.length == 1) {
                checked_radio = checked_radio[0];
                // if the user is adding a new payment
                if(this.isNewPaymentRadio(checked_radio)) {
                    var acquirer_id = this.getAcquirerIdFromRadio(checked_radio);
                    var acquirer_form = this.$('#o_payment_add_token_acq_' + acquirer_id);
                    // we retrieve all the input inside the acquirer form and 'serialize' them to an indexed array
                    var form_data = this.getFormData($('input', acquirer_form));
                    var ds = $('input[name="data_set"]', acquirer_form)[0];
                    $(button).attr('disabled', true);
                    $(button).prepend('<span class="o_loader"><i class="fa fa-refresh fa-spin"></i>&nbsp;</span>');

                    var verify_validity = this.$el.find('input[name="verify_validity"]');

                    if(verify_validity.length>0)
                        form_data.verify_validity = verify_validity[0].value === "1";

                    // do the call to the route stored in the 'data_set' input of the acquirer form, the data must be called 'create-route'
                    ajax.jsonRpc(ds.dataset.createRoute, 'call', form_data).then(function(data) {
                        // if the server has returned true
                        if(data.result) {
                            // and it need a 3DS authentication
                            if(data['3d_secure'] !== false) {
                                // then we display the 3DS page to the user
                                $("body").html(data['3d_secure']);
                            }
                            else {
                                checked_radio.value = data.id; // set the radio value to the new card id
                                form.submit();
                            }
                        }
                        // if the server has returned false, we display an error
                        else {
                            self.error(_t('Error'),
                                _t("<p>We are not able to add your payment method at the moment.</p>"));
                        }
                        // here we remove the 'processing' icon from the 'add a new payment' button
                        $(button).attr('disabled', false);
                        $(button).find('span.o_loader').remove();
                    }).fail(function(message, data) {
                        // if the rpc fails, pretty obvious
                        $(button).attr('disabled', false);
                        $(button).find('span.o_loader').remove();

                        self.error(_t('Error'),
                            _t("<p>We are not able to add your payment method at the moment.</p>") + (core.debug ? data.data.message : ''));
                    });
                }
                // if the user is using an old payment
                else {
                    // then we just submit the form
                    form.submit();
                }
            }
            else {
                this.error(_t('Error'),
                    _t('<p>Please select a payment method</p>'));
            }
        },
        // event handler when clicking on the button to add a new payment method
        addPmEvent: function(ev) {
            ev.stopPropagation();
            ev.preventDefault();
            var form = this.el;
            var checked_radio = this.$('input[type="radio"]:checked');
            var self = this;
            var button = ev.target;

            // we check if the user has selected a 'add a new payment' option
            if(checked_radio.length == 1 && this.isNewPaymentRadio(checked_radio[0])) {
                // then we add a 'processing' icon into the 'add a new payment' button
                $(button).attr('disabled', true);
                $(button).prepend('<span class="o_loader"><i class="fa fa-refresh fa-spin"></i>&nbsp;</span>');
                // we retrieve which acquirer is used
                checked_radio = checked_radio[0];
                var acquirer_id = this.getAcquirerIdFromRadio(checked_radio);
                var acquirer_form = this.$('#o_payment_add_token_acq_' + acquirer_id);
                // we retrieve all the input inside the acquirer form and 'serialize' them to an indexed array
                var form_data = this.getFormData($('input', acquirer_form));
                var ds = $('input[name="data_set"]', acquirer_form)[0];

                // we force the check when adding a card trough here
                form_data.verify_validity = true;

                // do the call to the route stored in the 'data_set' input of the acquirer form, the data must be called 'create-route'
                ajax.jsonRpc(ds.dataset.createRoute, 'call', form_data).then(function(data) {
                    // if the server has returned true
                    if(data.result) {
                        // and it need a 3DS authentication
                        if(data['3d_secure'] !== false) {
                            // then we display the 3DS page to the user
                            $("body").html(data['3d_secure']);
                        }
                        // if it doesn't require 3DS
                        else {
                            // we just go to the return_url or reload the page
                            if(form_data.return_url) {
                                window.location = form_data.return_url;
                            }
                            else {
                                window.location.reload();
                            }
                        }
                    }
                    // if the server has returned false, we display an error
                    else {
                        self.error(_t('Error'),
                            _t("<p>We are not able to add your payment method at the moment.</p>"));
                    }
                    // here we remove the 'processing' icon from the 'add a new payment' button
                    $(button).attr('disabled', false);
                    $(button).find('span.o_loader').remove();
                }).fail(function(message, data) {
                    // if the rpc fails, pretty obvious
                    $(button).attr('disabled', false);
                    $(button).find('span.o_loader').remove();

                    self.error(_t('Error'),
                        _t("<p>We are not able to add your payment method at the moment.</p>") + (core.debug ? data.data.message : ''));
                });
            }
            else {
                this.error(_t('Error'),
                    _t('<p>Please select the option to add a new payment method</p>'));
            }
        },
        // event handler when clicking on a button to delete a payment method
        deletePmEvent: function (ev) {
            ev.stopPropagation();
            ev.preventDefault();
            var self = this;
            var pm_id = parseInt(ev.target.value);

            var Delete = function() {
                rpc.query({
                        model: 'payment.token',
                        method: 'unlink',
                        args: [pm_id],
                    })
                    .then(function(result){
                        if(result === true) {
                            ev.target.closest('div').remove();
                        }
                    },function(type,err){
                        self.error(_t('Error'),
                            _t("<p>We are not able to delete your payment method at the moment.</p>"));
                    });
            };

            rpc.query({
                model: 'payment.token',
                method: 'get_linked_records',
                args: [pm_id],
            }).then(function(result){
                if(result[pm_id].length > 0) {
                    // if there's records linked to this payment method
                    var content = '';
                    result[pm_id].forEach(function(sub) {
                        content += '<p><a href="' + sub.url + '" title="' + _.str.escapeHTML(sub.description) + '">' + _.str.escapeHTML(sub.name) + '</a><p/>';
                    });

                    content = $('<div>').html(_t('<p>This card is currently linked to the following records:<p/>') + content);
                    // Then we display the list of the records and ask the user if he really want to remove the ppayment method.
                    new Dialog(self, {
                        title: _t('Warning!'),
                        size: 'medium',
                        $content: content,
                        buttons: [
                        {text: _t('Confirm Deletion'), classes: 'btn-primary', close: true, click: Delete},
                        {text: _t('Cancel'), close: true}]}).open();
                }
                else {
                    // if there's no records linked to this payment method, then we delete it
                    Delete();
                }
            }, function(type, err){
                self.error(_t('Error'),
                    _t("<p>We are not able to delete your payment method at the moment.</p>") + (core.debug ? err.data.message : ''));
            });
        },
        // event handler when clicking on a radio button
        radioClickEvent: function(ev) {
            this.updateNewPaymentDisplayStatus();
        },
        updateNewPaymentDisplayStatus: function()
        {
            var checked_radio = this.$('input[type="radio"]:checked');
            // we hide all the acquirers form
            this.$('[id*="o_payment_add_token_acq_"]').addClass('hidden');
            // if we clicked on an add new payment radio
            if(checked_radio.length == 1 && this.isNewPaymentRadio(checked_radio[0]))
            {
                // then we retrieve the acquirer name
                var acquirer_id = this.getAcquirerIdFromRadio(checked_radio[0]);
                // and display its form
                this.$('#o_payment_add_token_acq_' + acquirer_id).removeClass('hidden');
            }
        },
        isNewPaymentRadio: function(element) {
            return $(element).data('acquirer-id') !== undefined;
        },
        getAcquirerIdFromRadio: function(element) {
            return $(element).data('acquirer-id');
        },
        error: function(title, message, url) {
            return new Dialog(null, {
                title: title || "",
                $content: $(core.qweb.render('website.error_dialog', {
                    message: message || "",
                })),
            }).open();
        },
        getFormData: function($form){
            var unindexed_array = $form.serializeArray();
            var indexed_array = {};

            $.map(unindexed_array, function(n, i){
                indexed_array[n.name] = n.value;
            });
            return indexed_array;
        },
        start: function() {
            this.updateNewPaymentDisplayStatus();
        },
    });



    $(document).ready(function (){
        var form = new PaymentForm();
        form.attachTo($('.o_payment_form'));
    });
});
