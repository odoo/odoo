odoo.define('payment_razorpay.razorpay', function(require) {
    "use strict";

    var ajax = require('web.ajax');
    var core = require('web.core');
    var _t = core._t;
    var qweb = core.qweb;
    ajax.loadXML('/payment_razorpay/static/src/xml/payment_razorpay_templates.xml', qweb);

    require('web.dom_ready');
    if (!$('.o_payment_form').length) {
        return $.Deferred().reject("DOM doesn't contain '.o_payment_form'");
    }

    var observer = new MutationObserver(function(mutations, observer) {
        for(var i=0; i<mutations.length; ++i) {
            for(var j=0; j<mutations[i].addedNodes.length; ++j) {
                if(mutations[i].addedNodes[j].tagName.toLowerCase() === "form" && mutations[i].addedNodes[j].getAttribute('provider') == 'razorpay') {
                    display_razorpay_form($(mutations[i].addedNodes[j]));
                }
            }
        }
    });

    function razorpay_show_error(msg) {
        var wizard = $(qweb.render('razorpay.error', {'msg': msg || _t('Payment error')}));
        wizard.appendTo($('body')).modal({'keyboard': true});
    };

    function razorpay_handler(resp) {
        if (resp.razorpay_payment_id) {
            $.post('/payment/razorpay/capture',{
                payment_id: resp.razorpay_payment_id,
            }).done(function (data) {
                window.location.href = data;
            }).fail(function (data) {
                razorpay_show_error(data && data.data && data.data.message);
            });
        }
    };

    function display_razorpay_form(provider_form) {
        // Open Checkout with further options
        var payment_form = $('.o_payment_form');
        if(!payment_form.find('i').length)
        {
            payment_form.append('<i class="fa fa-spinner fa-spin"/>');
            payment_form.attr('disabled','disabled');
        }

        var get_input_value = function (name) {
            return provider_form.find('input[name="' + name + '"]').val();
        }
        var primaryColor = getComputedStyle(document.body).getPropertyValue('--primary');
        var options = {
            "key": get_input_value('key'),
            "amount": get_input_value('amount'),
            "name": get_input_value('merchant_name'),
            "description": get_input_value('description'),
            "handler": razorpay_handler,
            "modal": {
                "ondismiss": function() { window.location.reload(); },
                'backdropclose': function() { window.location.reload(); }
            },
            'prefill': {
                'name': get_input_value('name'),
                'contact': get_input_value('contact'),
                'email': get_input_value('email')
            },
            'notes': {
                'order_id': get_input_value('order_id'),
            },
            "theme": {
                "color": primaryColor
            },
        }
        var rzp1 = new Razorpay(options);
        rzp1.open();
    };

    $.getScript("https://checkout.razorpay.com/v1/checkout.js", function (data, textStatus, jqxhr) {
        observer.observe(document.body, {childList: true});
        display_razorpay_form($('form[provider="razorpay"]'));
    });
});
