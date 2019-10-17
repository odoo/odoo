odoo.define('payment_stripe_sca.website_quote', function (require) {
    "use strict";

if(!$('.o_website_quote').length) {
    return $.Deferred().reject("DOM doesn't contain '.o_website_quote'");
}
var StripePortalMixin = require('payment_stripe_sca.website_mixin');
var WebsiteQuotePayment = require('website_quote.payment_method');

WebsiteQuotePayment.include(StripePortalMixin);
});
