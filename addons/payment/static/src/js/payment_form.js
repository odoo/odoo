odoo.define('payment.payment_form', function (require) {
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
            'click input[type="radio"]': 'radioClickEvent',
            'click .o_payment_form_pay_icon_more': 'onClickMorePaymentIcon',
        },

        init: function(parent, options) {
            this._super.apply(this, arguments);
            this.options = _.extend(options || {}, {
            });
        },

        start: function () {
            this.updateNewPaymentDisplayStatus();
            $('[data-toggle="tooltip"]').tooltip();
        },

        payEvent: function (ev) {
            ev.preventDefault();
            var form = this.el;
            var checked_radio = this.$('input[type="radio"]:checked');
            var self = this;
            var button = ev.target;

            // first we check that the user has selected a payment method
            if (checked_radio.length === 1) {
                checked_radio = checked_radio[0];

                // we retrieve all the input inside the acquirer form and 'serialize' them to an indexed array
                var acquirer_id = this.getAcquirerIdFromRadio(checked_radio);
                var acquirer_form = false;
                if (this.isNewPaymentRadio(checked_radio)) {
                    acquirer_form = this.$('#o_payment_add_token_acq_' + acquirer_id);
                } else {
                    acquirer_form = this.$('#o_payment_form_acq_' + acquirer_id);
                }
                var inputs_form = $('input', acquirer_form);
                var ds = $('input[name="data_set"]', acquirer_form)[0];

                // if the user is adding a new payment
                if (this.isNewPaymentRadio(checked_radio)) {
                    if (this.options.partnerId === undefined) {
                        console.warn('payment_form: unset partner_id when adding new token; things could go wrong');
                    }
                    var form_data = this.getFormData(inputs_form);
                    var empty_inputs = false;

                    inputs_form.toArray().forEach(function (element) {
                        if (element.dataset.isRequired) {
                            if (element.value.length === 0) {
                                $(element).closest('div.form-group').addClass('has-error');
                                empty_inputs = true;
                            }
                            else {
                                $(element).closest('div.form-group').removeClass('has-error');
                            }
                        }
                    });

                    if (empty_inputs) {
                        this.displayError(
                            _t('Missing values'),
                            _t('<p>Please fill all the inputs required.</p>')
                        );
                        return;
                    }

                    $(button).attr('disabled', true);
                    $(button).prepend('<span class="o_loader"><i class="fa fa-refresh fa-spin"></i>&nbsp;</span>');

                    var verify_validity = this.$el.find('input[name="verify_validity"]');

                    if (verify_validity.length>0) {
                        form_data.verify_validity = verify_validity[0].value === "1";
                    }

                    // do the call to the route stored in the 'data_set' input of the acquirer form, the data must be called 'create-route'
                    ajax.jsonRpc(ds.dataset.createRoute, 'call', form_data).then(function (data) {
                        // if the server has returned true
                        if (data.result) {
                            // and it need a 3DS authentication
                            if (data['3d_secure'] !== false) {
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
                            self.displayError(
                                _t('Server Error'),
                                _t("<p>We are not able to add your payment method at the moment.</p>"));
                        }
                        // here we remove the 'processing' icon from the 'add a new payment' button
                        $(button).attr('disabled', false);
                        $(button).find('span.o_loader').remove();
                    }).fail(function (message, data) {
                        // if the rpc fails, pretty obvious
                        $(button).attr('disabled', false);
                        $(button).find('span.o_loader').remove();

                        self.displayError(
                            _t('Server Error'),
                            _t("<p>We are not able to add your payment method at the moment.</p>") +
                               "<p>" +
                               (core.debug ? (data.data.message.replace(/\n/g, "<br />")): '') +
                               "</p>"
                        );
                    });
                }
                // if the user is going to pay with a form payment, then
                else if (this.isFormPaymentRadio(checked_radio)) {
                    var $tx_url = this.$el.find('input[name="prepare_tx_url"]');
                    // if there's a prepare tx url set
                    if ($tx_url.length === 1) {
                        // if the user wants to save his credit card info
                        var form_save_token = $('input[name="o_payment_form_save_token"]').prop('checked');
                        // then we call the route to prepare the transaction
                        ajax.jsonRpc($tx_url[0].value, 'call', {
                            'acquirer_id': parseInt(acquirer_id),
                            'save_token': form_save_token,
                            'access_token': self.options.accessToken,
                            'success_url': self.options.successUrl,
                            'error_url': self.options.errorUrl,
                            'callback_method': self.options.callbackMethod,
                        }).then(function (result) {
                            if (result) {
                                // if the server sent us the html form, we create a form element
                                var newForm = document.createElement('form');
                                newForm.setAttribute("method", "post"); // set it to post
                                newForm.setAttribute("provider", checked_radio.dataset.provider);
                                newForm.hidden = true; // hide it
                                newForm.innerHTML = result; // put the html sent by the server inside the form
                                var action_url = $(newForm).find('input[name="data_set"]').data('actionUrl');
                                newForm.setAttribute("action", action_url); // set the action url
                                $(document.getElementsByTagName('body')[0]).append(newForm); // append the form to the body
                                $(newForm).find('input[data-remove-me]').remove(); // remove all the input that should be removed
                                if(action_url) {
                                    newForm.submit(); // and finally submit the form
                                }
                            }
                            else {
                                self.displayError(
                                    _t('Server Error'),
                                    _t("<p>We are not able to redirect you to the payment form.</p>")
                                );
                            }
                        }).fail(function (message, data) {
                            self.displayError(
                                _t('Server Error'),
                                _t("<p>We are not able to redirect you to the payment form.</p>") +
                                   "<p>" +
                                   (core.debug ? (data.data.message.replace(/\n/g, "<br />")): '') +
                                   "</p>"
                            );
                        });
                    }
                    else {
                        // we append the form to the body and send it.
                        this.displayError(
                            _t("Cannot set-up the payment"),
                            _t("<p>We're unable to process your payment.</p>")
                        );
                    }
                }
                else {  // if the user is using an old payment then we just submit the form
                    form.submit();
                }
            }
            else {
                this.displayError(
                    _t('No payment method selected'),
                    _t('<p>Please select a payment method.</p>')
                );
            }
        },
        // event handler when clicking on the button to add a new payment method
        addPmEvent: function (ev) {
            ev.stopPropagation();
            ev.preventDefault();
            var checked_radio = this.$('input[type="radio"]:checked');
            var self = this;
            var button = ev.target;

            // we check if the user has selected a 'add a new payment' option
            if (checked_radio.length === 1 && this.isNewPaymentRadio(checked_radio[0])) {
                // we retrieve which acquirer is used
                checked_radio = checked_radio[0];
                var acquirer_id = this.getAcquirerIdFromRadio(checked_radio);
                var acquirer_form = this.$('#o_payment_add_token_acq_' + acquirer_id);
                // we retrieve all the input inside the acquirer form and 'serialize' them to an indexed array
                var inputs_form = $('input', acquirer_form);
                var form_data = this.getFormData(inputs_form);
                var ds = $('input[name="data_set"]', acquirer_form)[0];
                var empty_inputs = false;

                inputs_form.toArray().forEach(function (element) {
                    if (element.dataset.isRequired) {
                        if (element.value.length === 0) {
                            $(element).closest('div.form-group').addClass('has-error');
                            empty_inputs = true;
                        }
                        else {
                            $(element).closest('div.form-group').removeClass('has-error');
                        }
                    }
                });

                if (empty_inputs) {
                    this.displayError(
                        _t('Missing values'),
                        _t('<p>Please fill all the inputs required.</p>')
                    );
                    return;
                }
                // We add a 'processing' icon into the 'add a new payment' button
                $(button).attr('disabled', true);
                $(button).prepend('<span class="o_loader"><i class="fa fa-refresh fa-spin"></i>&nbsp;</span>');

                // we force the check when adding a card trough here
                form_data.verify_validity = true;

                // do the call to the route stored in the 'data_set' input of the acquirer form, the data must be called 'create-route'
                ajax.jsonRpc(ds.dataset.createRoute, 'call', form_data).then( function (data) {
                    // if the server has returned true
                    if (data.result) {
                        // and it need a 3DS authentication
                        if (data['3d_secure'] !== false) {
                            // then we display the 3DS page to the user
                            $("body").html(data['3d_secure']);
                        }
                        // if it doesn't require 3DS
                        else {
                            // we just go to the return_url or reload the page
                            if (form_data.return_url) {
                                window.location = form_data.return_url;
                            }
                            else {
                                window.location.reload();
                            }
                        }
                    }
                    // if the server has returned false, we display an error
                    else {
                        self.displayError(
                            _t('Server Error'),
                            _t("<p>We are not able to add your payment method at the moment.</p>")
                        );
                    }
                    // here we remove the 'processing' icon from the 'add a new payment' button
                    $(button).attr('disabled', false);
                    $(button).find('span.o_loader').remove();
                }).fail(function (message, data) {
                    // if the rpc fails, pretty obvious
                    $(button).attr('disabled', false);
                    $(button).find('span.o_loader').remove();

                    self.displayError(
                        _t('Server error'),
                        _t("<p>We are not able to add your payment method at the moment.</p>") +
                           "<p>" +
                           (core.debug ? (data.data.message.replace(/\n/g, "<br />")): '') +
                           "</p>"
                    );
                });
            }
            else {
                this.displayError(
                    _t('No payment method selected'),
                    _t('<p>Please select the option to add a new payment method.</p>')
                );
            }
        },
        // event handler when clicking on a button to delete a payment method
        deletePmEvent: function (ev) {
            ev.stopPropagation();
            ev.preventDefault();
            var self = this;
            var pm_id = parseInt(ev.target.value);

            var tokenDelete = function () {
                rpc.query({
                        model: 'payment.token',
                        method: 'unlink',
                        args: [pm_id],
                    })
                    .then(function (result) {
                        if ( result === true) {
                            ev.target.closest('div').remove();
                        }
                    }, function () {
                        self.displayError(
                            _t('Server Error'),
                            _t("<p>We are not able to delete your payment method at the moment.</p>")
                        );
                    });
            };

            rpc.query({
                model: 'payment.token',
                method: 'get_linked_records',
                args: [pm_id],
            }).then(function (result) {
                if (result[pm_id].length > 0) {
                    // if there's records linked to this payment method
                    var content = '';
                    result[pm_id].forEach(function (sub) {
                        content += '<p><a href="' + sub.url + '" title="' + _.str.escapeHTML(sub.description) + '">' + _.str.escapeHTML(sub.name) + '</a><p/>';
                    });

                    content = $('<div>').html(_t('<p>This card is currently linked to the following records:<p/>') + content);
                    // Then we display the list of the records and ask the user if he really want to remove the payment method.
                    new Dialog(self, {
                        title: _t('Warning!'),
                        size: 'medium',
                        $content: content,
                        buttons: [
                        {text: _t('Confirm Deletion'), classes: 'btn-primary', close: true, click: tokenDelete},
                        {text: _t('Cancel'), close: true}]
                    }).open();
                }
                else {
                    // if there's no records linked to this payment method, then we delete it
                    tokenDelete();
                }
            }, function (type, err) {
                self.displayError(
                    _t('Server Error'),
                    _t("<p>We are not able to delete your payment method at the moment.</p>") + (core.debug ? err.data.message : '')
                );
            });
        },

        // event handler when clicking on 'and more' to show more payment icon
        onClickMorePaymentIcon: function (ev) {
            ev.preventDefault();
            var $listItems = $(ev.currentTarget).parents('ul').children('li');
            var $moreItem = $(ev.currentTarget).parents('li');
            $listItems.removeClass('hidden');
            $moreItem.addClass('hidden');
        },

        // event handler when clicking on a radio button
        radioClickEvent: function (ev) {
            this.updateNewPaymentDisplayStatus();
        },
        updateNewPaymentDisplayStatus: function ()
        {
            var checked_radio = this.$('input[type="radio"]:checked');
            // we hide all the acquirers form
            this.$('[id*="o_payment_add_token_acq_"]').addClass('hidden');
            this.$('[id*="o_payment_form_acq_"]').addClass('hidden');
            if (checked_radio.length !== 1) {
                return;
            }
            checked_radio = checked_radio[0];
            var acquirer_id = this.getAcquirerIdFromRadio(checked_radio);

            // if we clicked on an add new payment radio, display its form
            if (this.isNewPaymentRadio(checked_radio)) {                
                this.$('#o_payment_add_token_acq_' + acquirer_id).removeClass('hidden');
            }
            else if (this.isFormPaymentRadio(checked_radio)) {
                this.$('#o_payment_form_acq_' + acquirer_id).removeClass('hidden');
            }
        },
        isNewPaymentRadio: function (element) {
            return $(element).data('s2s-payment') === 'True';
        },
        isFormPaymentRadio: function (element) {
            return $(element).data('form-payment') === 'True';
        },
        getAcquirerIdFromRadio: function (element) {
            return $(element).data('acquirer-id');
        },
        displayError: function (title, message) {
            return new Dialog(null, {
                title: _t('Error: ') + title,
                size: 'medium',
                $content: message || "",
                buttons: [
                {text: _t('Ok'), close: true}]}).open();
        },
        getFormData: function ($form) {
            var unindexed_array = $form.serializeArray();
            var indexed_array = {};

            $.map(unindexed_array, function (n, i) {
                indexed_array[n.name] = n.value;
            });
            return indexed_array;
        },
    });

    $(function () {
        // TODO move this to another module, requiring dom_ready and rejecting
        // the returned deferred to get the proper message
        if (!$('.o_payment_form').length) {
            console.log("DOM doesn't contain '.o_payment_form'");
            return;
        }
        $('.o_payment_form').each(function () {
            var $elem = $(this);
            var form = new PaymentForm(null, $elem.data());
            form.attachTo($elem);
        });
    });

    return PaymentForm;
});
