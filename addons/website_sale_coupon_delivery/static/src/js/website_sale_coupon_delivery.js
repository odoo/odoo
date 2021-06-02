odoo.define('website_sale_coupon_delivery.checkout', function (require) {
'use strict';

var core = require('web.core');
var publicWidget = require('web.public.widget');
require('website_sale_delivery.checkout');

var _t = core._t;

publicWidget.registry.websiteSaleDelivery.include({

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _handleCarrierUpdateResult: function (result) {
        this._super.apply(this, arguments);
        if (result.new_amount_order_discounted) {
            // Update discount of the order
            $('#order_discounted').html(result.new_amount_order_discounted);
        }
    },
    /**
     * @override
     */
    _handleCarrierUpdateResultBadge: function (result) {
        this._super.apply(this, arguments);
        if (result.new_amount_order_discounted) {
            // We are in freeshipping, so every carrier is Free but we don't
            // want to replace error message by 'Free'
            $('#delivery_carrier .badge:not(.o_wsale_delivery_carrier_error)').text(_t('Free'));
        }
    },
});
});
