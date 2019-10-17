odoo.define('payment_stripe_sca.website_sale_payment', function (require) {
    "use strict";

if(!$('.oe_website_sale').length) {
    return $.Deferred().reject("DOM doesn't contain '.oe_website_sale'");
}

var StripePortalMixin = require('payment_stripe_sca.website_mixin');
var WebsiteSalePayment = require('website_sale.payment');

WebsiteSalePayment.include(StripePortalMixin);
});
