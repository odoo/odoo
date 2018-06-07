odoo.define('payment_stripe.stripe', function(require) {
    "use strict";

    var ajax = require('web.ajax');
    var core = require('web.core');
    var rpc = require('web.rpc');
    var qweb = core.qweb;
    ajax.loadXML('/payment_stripe/static/src/xml/stripe_templates.xml', qweb);

    require('web.dom_ready');
    if (!$('.o_payment_form').length) {
        return $.Deferred().reject("DOM doesn't contain '.o_payment_form'");
    }

    var observer = new MutationObserver(function(mutations, observer) {
        for(var i=0; i<mutations.length; ++i) {
            for(var j=0; j<mutations[i].addedNodes.length; ++j) {
                if(mutations[i].addedNodes[j].tagName.toLowerCase() === "form" && mutations[i].addedNodes[j].getAttribute('provider') == 'stripe') {
                    do_stripe_payment($(mutations[i].addedNodes[j]));
                }
            }
        }
    });

    function display_error(message, acquirer_id) {
        $('#payment_error').remove();
        var $acquirerForm = $('#o_payment_form_acq_' + acquirer_id);
        var $message = $('<div>', {
            class: 'alert alert-danger mx-4',
            text:  _.str.escapeHTML(message),
            id: 'payment_error',
        });
        $acquirerForm.append($message);
        $("#o_payment_form_pay").removeAttr('disabled');
    }

    function stripeTokenHandler(token, provider_form) {
        // Insert the token ID into the form so it gets submitted to the server
        var $form = $('#payment-form');
        var $hiddenInput = $('<input>', {
            type: 'hidden',
            name: 'stripeToken',
            value: token.id
        });
        $form.append($hiddenInput);
        $form.append(provider_form.find('input'));
        $form.submit();
    }

    function create_stripe_token(stripe, provider_form, type) {
        var $modal = $('#payment-element-modal');
        if ($modal.length) {
            $modal.modal('show');
        } else {
            var element = stripe.elements();
            var paymentelement = element.create(type);
            var wizard = $(qweb.render('stripe.payment.element', {type: type}));
            wizard.appendTo($('body')).modal({'keyboard': true});
            paymentelement.mount('#card-element');
            paymentelement.addEventListener('change', function(event) {
                var displayError = document.getElementById('card-errors');
                displayError.textContent = '';
                if (event.error) {
                    displayError.textContent = event.error.message;
                }
            });
            var form = document.getElementById('payment-form');
            form.addEventListener('submit', function(event) {
                event.preventDefault();
                stripe.createToken(paymentelement).then(function(result) {
                    if (result.error) {
                        // Inform the user if there was an error.
                        var errorElement = document.getElementById('card-errors');
                        errorElement.textContent = result.error.message;
                    } else {
                        // Send the token to server.
                        stripeTokenHandler(result.token, provider_form);
                    }
                });
            });
        }
    }

    function do_stripe_payment(provider_form) {
        // Open Checkout with further options
        var payment_form = $('.o_payment_form');
        if(!payment_form.find('i').length)
            payment_form.append('<i class="fa fa-spinner fa-spin"/>');
            payment_form.attr('disabled','disabled');

        var get_input_value = function(name) {
            return provider_form.find('input[name="' + name + '"]').val();
        }

        var acquirer_id = parseInt(get_input_value('acquirer'));
        var amount = parseFloat(get_input_value("amount") || '0.0');
        var currency = get_input_value("currency");
        var email = get_input_value("email");
        $('#payment_error').remove();
        var $select = payment_form.find('.stripe_payment_type');
        var type = $select.val().toLowerCase().replace(/\ /g, '_');
        var stripe = Stripe(get_input_value('stripe_key'));
        if (_.contains(['card', 'sepa_debit'], type)) {
            return create_stripe_token(stripe, provider_form, type);
        }
        var data = {
            'type': type,
            'owner[name]': get_input_value('name'),
            'owner[email]': email,
            'redirect[return_url]': get_input_value('redirect_url'),
            'amount': parseInt(amount * 100),
            'currency': currency,
            'metadata[reference]': get_input_value('reference'),
            'owner[address][city]': get_input_value('city'),
            'owner[address][line1]': get_input_value('line1'),
            'owner[address][state]': get_input_value('state'),
            'owner[address][country]': get_input_value('country'),
            'owner[address][postal_code]': get_input_value('postal_code'),
        }
        if (type == 'sofort') {
            data = _.extend({}, data, {
                'sofort[country]': get_input_value('country')
            });
        }
        stripe.createSource(data).then(function (result) {
            if (result.error) {
                display_error(result.error.message, acquirer_id);
            } else {
                if (result.source.flow === 'redirect' || result.source.type === 'multibanco') {
                    window.location.href = result.source.redirect.url;
                }
                else if (result.source.type == 'wechat') {
                    rpc.query({
                        route: '/stripe/generate_qrcode',
                        params: {'qr_code_url': result.source.wechat.qr_code_url},
                    }).then(function(res) {
                        var wizard = $(qweb.render('stripe.payment.element', {type: result.source.type, qr_image: res}));
                        wizard.appendTo($('body')).modal({'keyboard': true});
                    })

                }
            }
        });
    }

    if (!window.strip_loaded) {
        $.getScript("https://js.stripe.com/v3/", function(data, textStatus, jqxhr) {
            observer.observe(document.body, {childList: true});
            do_stripe_payment($('form[provider="stripe"]'));
            window.strip_loaded = true;
        });
    }
});