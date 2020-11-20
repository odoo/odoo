odoo.define('payment_ogone.payment_feedback', function (require) {
    "use strict";
    const publicWidget = require('web.public.widget');
    const PaymentCheckoutForm = require('payment.checkout_form');
    const core = require('web.core');

    publicWidget.registry.ogoneFeedback = PaymentCheckoutForm.extend({
        selector: '.o_payment_feedback',
        start: function () {
            if (document.URL.indexOf("final") > 0) {
                // We are coming back from the 3DS verification
                window.top.location = '/payment/status';
            } else {
                const urlParameters = this._getUrlParameters(document.URL);
                // Extract contextual values from the radio button
                const paymentOptionId = parseInt(urlParameters['paymentOptionId'], 10);
                const provider = 'ogone';
                const flow = 'direct';
                const feedbackParams = Object.assign({}, urlParameters, {provider: provider, flow: flow});
                this._ogoneMakePayment(feedbackParams);
            }
        },

        _getUrlParameters: function (url) {
            // Get the url parameters
            const rawParameters = url.split('?')[1].split('&');
            let config = {};
            rawParameters.forEach(option => {
                const splittedOption = option.split('=');
                config[splittedOption[0]] = splittedOption[1];
            });
            return config;
        },

        _ogoneMakePayment: function (data) {
            // We must init the tx.
            // urls are encoded twice: one in python and once by Ogone when we come back from the FlexAPI.

            const initTxRoute = decodeURIComponent(decodeURIComponent(data.initTxRoute));
            const validationRoute = data.validationRoute ? decodeURIComponent(decodeURIComponent(data.validationRoute)) : false;
            const landingRoute = decodeURIComponent(decodeURIComponent(data.landingRoute));

            this.txContext = {
                initTxRoute: initTxRoute,
                validationRoute: validationRoute,
                landingRoute: landingRoute,
                referencePrefix: data.referencePrefix,
                amount: data.amount !== undefined ? parseFloat(data.amount) : null,
                currencyId: data.currencyId,
                partnerId: data.partnerId !== undefined ? parseInt(data.partnerId) : null,
                flow: data.flow,
                tokenizationRequested: data['Alias.StorePermanently'] === 'Y' ? true : false,
                accessToken: data.access_token,
                csrf_token: core.csrf_token,
            };

            const paymentOptionId = data.paymentOptionId !== undefined ? parseInt(data.paymentOptionId) : null;
            const acquirerId = data.acquirerId !== undefined ? parseFloat(data.acquirerId) : null;
            const ogoneValues = {
                'Alias.AliasId': data['Alias.AliasId'],
                'Alias.NCError': data['Alias.NCError'],
                'Alias.NCErrorCN': data['Alias.NCErrorCN'],
                'Alias.NCErrorCVC': data['Alias.NCErrorCVC'],
                'Alias.NCErrorCardNo': data['Alias.NCErrorCardNo'],
                'Alias.NCErrorED': data['Alias.NCErrorED'],
                'Alias.OrderId': data['Alias.OrderId'],
                'Alias.Status': data['Alias.Status'],
                'Alias.StorePermanently': data['Alias.StorePermanently'],
                'Card.Bin': data['Card.Bin'],
                'Card.Brand': data['Card.Brand'],
                'Card.CardHolderName': data['Card.CardHolderName'],
                'Card.CardNumber': data['Card.CardNumber'],
                'Card.Cvc': data['Card.Cvc'],
                'Card.ExpiryDate': data['Card.ExpiryDate'],
                SHASign: data.SHASign,
                referencePrefix: data['referencePrefix'],
                // 3ds2 parameters
                browserColorDepth: screen.colorDepth,
                browserJavaEnabled: navigator.javaEnabled(),
                browserLanguage: navigator.language,
                browserScreenHeight: screen.height,
                browserScreenWidth: screen.width,
                browserTimeZone: new Date().getTimezoneOffset(),
                browserUserAgent: navigator.userAgent,
                type: 'flexcheckout',
                acquirer_id: acquirerId,
            };
            const self = this;
            return this._rpc({
                route: this.txContext.initTxRoute,
                params: this._prepareInitTxParams('ogone', paymentOptionId, data.flow),
            }).then(processingValues => {
                ogoneValues['reference'] = processingValues.reference;
                ogoneValues['partner_id'] = processingValues.partner_id;
                return this._rpc({
                    route: '/payment/ogone/payments',
                    params: {
                        'acquirer_id': acquirerId,
                        'ogone_values': ogoneValues,
                    },
                });
            }).then(result => {
                // We redirect the parent page to the payment status page
                if (result.tx_status === 'pending' && result.hasOwnProperty('html_3ds')) {
                    document.getElementById("payment_feedback").innerHTML = result.html_3ds;
                    // 3ds inside the iframe; self is defined in the html_3ds html
                    const downloadform3D = document.getElementById("downloadform3D");
                    downloadform3D.submit();
                } else if (result.ogone_user_error) {
                    // We display a translated error messag corresponding to the backlog of Ogone
                    document.getElementsByClassName("o_ogone_spinner")[0].style.display = 'none';
                    document.getElementsByClassName("o_ogone_error_message")[0].style.display = 'block';
                    document.getElementsByClassName("o_ogone_error_name")[0].innerText = result.ogone_user_error;
                    document.getElementById('btn_payment_status').addEventListener("click", button => {
                        window.top.location = '/payment/status';
                    });
                } else {
                    window.top.location = '/payment/status';
                }
            });
        },


    });
});
