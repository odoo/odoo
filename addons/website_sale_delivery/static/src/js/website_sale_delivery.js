odoo.define('website_sale_delivery.checkout', function (require) {
'use strict';

var core = require('web.core');
var sAnimations = require('website.content.snippets.animation');

var _t = core._t;

sAnimations.registry.websiteSaleDelivery = sAnimations.Class.extend({
    selector: '.oe_website_sale',
    read_events: {
        'change select[name="shipping_id"]': '_onSetAddress',
        'click #delivery_carrier input[name="delivery_type"]': '_onCarrierClick',
    },

    /**
     * @override
     */
    start: function () {
        var $carriers = $('#delivery_carrier input[name="delivery_type"]');
        // Workaround to:
        // - update the amount/error on the label at first rendering
        // - prevent clicking on 'Pay Now' if the shipper rating fails
        if ($carriers.length > 0) {
            $carriers.filter(':checked').click();
        }
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Object} result
     */
    _handleCarrierUpdateResult: function (result) {
        var $payButton = $('#o_payment_form_pay');
        var $amountDelivery = $('#order_delivery span.oe_currency_value');
        var $amountUntaxed = $('#order_total_untaxed span.oe_currency_value');
        var $amountTax = $('#order_total_taxes span.oe_currency_value');
        var $amountTotal = $('#order_total span.oe_currency_value');
        var $carrierBadge = $('#delivery_carrier input[name="delivery_type"][value=' + result.carrier_id + '] ~ .badge.d-none');
        var $computeBadge = $('#delivery_carrier input[name="delivery_type"][value=' + result.carrier_id + '] ~ .o_delivery_compute');
        var $discount = $('#order_discounted');

        if ($discount && result.new_amount_order_discounted) {
            // Cross module without bridge
            // Update discount of the order
            $discount.find('.oe_currency_value').text(result.new_amount_order_discounted);

            // We are in freeshipping, so every carrier is Free
            $('#delivery_carrier .badge').text(_t('Free'));
        }

        if (result.status === true) {
            $amountDelivery.text(result.new_amount_delivery);
            $amountUntaxed.text(result.new_amount_untaxed);
            $amountTax.text(result.new_amount_tax);
            $amountTotal.text(result.new_amount_total);
            $carrierBadge.children('span').text(result.new_amount_delivery);
            $carrierBadge.removeClass('d-none');
            $computeBadge.addClass('d-none');
            $payButton.prop('disabled', false);
        } else {
            console.error(result.error_message);
            $computeBadge.text(result.error_message);
            $amountDelivery.text(result.new_amount_delivery);
            $amountUntaxed.text(result.new_amount_untaxed);
            $amountTax.text(result.new_amount_tax);
            $amountTotal.text(result.new_amount_total);
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onCarrierClick: function (ev) {
        $('#o_payment_form_pay').prop('disabled', true);
        this._rpc({
            route: '/shop/update_carrier',
            params: {
                carrier_id: $(ev.currentTarget).val(),
            },
        }).then(this._handleCarrierUpdateResult.bind(this));
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onSetAddress: function (ev) {
        var value = $(ev.currentTarget).val();
        var $providerFree = $('select[name="country_id"]:not(.o_provider_restricted), select[name="state_id"]:not(.o_provider_restricted)');
        var $providerRestricted = $('select[name="country_id"].o_provider_restricted, select[name="state_id"].o_provider_restricted');
        if (value === 0) {
            // Ship to the same address : only show shipping countries available for billing
            $providerFree.hide().attr('disabled', true);
            $providerRestricted.show().attr('disabled', false).change();
        } else {
            // Create a new address : show all countries available for billing
            $providerFree.show().attr('disabled', false).change();
            $providerRestricted.hide().attr('disabled', true);
        }
    },
});
});
