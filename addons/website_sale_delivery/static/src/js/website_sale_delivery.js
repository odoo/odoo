odoo.define('website_sale_delivery.checkout', function (require) {
'use strict';

var core = require('web.core');
var publicWidget = require('web.public.widget');

var _t = core._t;
var concurrency = require('web.concurrency');
var dp = new concurrency.DropPrevious();

publicWidget.registry.websiteSaleDelivery = publicWidget.Widget.extend({
    selector: '.oe_website_sale',
    events: {
        'change select[name="shipping_id"]': '_onSetAddress',
        'click #delivery_carrier .o_delivery_carrier_select': '_onCarrierClick',
    },

    /**
     * @override
     */
    start: function () {
        var self = this;
        var $carriers = $('#delivery_carrier input[name="delivery_type"]');
        var $payButton = $('button[name="o_payment_submit_button"]');
        // Workaround to:
        // - update the amount/error on the label at first rendering
        // - prevent clicking on 'Pay Now' if the shipper rating fails
        if ($carriers.length > 0) {
            if ($carriers.filter(':checked').length === 0) {
                $payButton.prop('disabled', true);
                var disabledReasons = $payButton.data('disabled_reasons') || {};
                disabledReasons.carrier_selection = true;
                $payButton.data('disabled_reasons', disabledReasons);
            }
            $carriers.filter(':checked').click();
        }

        // Asynchronously retrieve every carrier price
        _.each($carriers, function (carrierInput, k) {
            self._showLoading($(carrierInput));
            self._rpc({
                route: '/shop/carrier_rate_shipment',
                params: {
                    'carrier_id': carrierInput.value,
                },
            }).then(self._handleCarrierUpdateResultBadge.bind(self));
        });

        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {jQuery} $carrierInput
     */
    _showLoading: function ($carrierInput) {
        $carrierInput.siblings('.o_wsale_delivery_badge_price').empty();
        $carrierInput.siblings('.o_wsale_delivery_badge_price').append('<span class="fa fa-circle-o-notch fa-spin"/>');
    },
    /**
     * Update the total cost according to the selected shipping method
     * 
     * @private
     * @param {float} amount : The new total amount of to be paid
     */
    _updateShippingCost: function(amount){
        core.bus.trigger('update_shipping_cost', amount);
    },
    /**
     * @private
     * @param {Object} result
     */
    _handleCarrierUpdateResult: function (result) {
        this._handleCarrierUpdateResultBadge(result);
        var $payButton = $('button[name="o_payment_submit_button"]');
        var $amountDelivery = $('#order_delivery .monetary_field');
        var $amountUntaxed = $('#order_total_untaxed .monetary_field');
        var $amountTax = $('#order_total_taxes .monetary_field');
        var $amountTotal = $('#order_total .monetary_field, #amount_total_summary.monetary_field');

        if (result.status === true) {
            $amountDelivery.html(result.new_amount_delivery);
            $amountUntaxed.html(result.new_amount_untaxed);
            $amountTax.html(result.new_amount_tax);
            $amountTotal.html(result.new_amount_total);
            var disabledReasons = $payButton.data('disabled_reasons') || {};
            disabledReasons.carrier_selection = false;
            $payButton.data('disabled_reasons', disabledReasons);
            $payButton.prop('disabled', _.contains($payButton.data('disabled_reasons'), true));
        } else {
            $amountDelivery.html(result.new_amount_delivery);
            $amountUntaxed.html(result.new_amount_untaxed);
            $amountTax.html(result.new_amount_tax);
            $amountTotal.html(result.new_amount_total);
        }
        if (result.new_amount_total_raw !== undefined) {
            this._updateShippingCost(result.new_amount_total_raw);
        }
    },
    /**
     * @private
     * @param {Object} result
     */
    _handleCarrierUpdateResultBadge: function (result) {
        var $carrierBadge = $('#delivery_carrier input[name="delivery_type"][value=' + result.carrier_id + '] ~ .o_wsale_delivery_badge_price');

        if (result.status === true) {
             // if free delivery (`free_over` field), show 'Free', not '$0'
             if (result.is_free_delivery) {
                 $carrierBadge.text(_t('Free'));
             } else {
                 $carrierBadge.html(result.new_amount_delivery);
             }
             $carrierBadge.removeClass('o_wsale_delivery_carrier_error');
        } else {
            $carrierBadge.addClass('o_wsale_delivery_carrier_error');
            $carrierBadge.text(result.error_message);
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
        var $radio = $(ev.currentTarget).find('input[type="radio"]');
        this._showLoading($radio);
        $radio.prop("checked", true);
        var $payButton = $('button[name="o_payment_submit_button"]');
        $payButton.prop('disabled', true);
        var disabledReasons = $payButton.data('disabled_reasons') || {};
        disabledReasons.carrier_selection = true;
        $payButton.data('disabled_reasons', disabledReasons);
        dp.add(this._rpc({
            route: '/shop/update_carrier',
            params: {
                carrier_id: $radio.val(),
            },
        })).then(this._handleCarrierUpdateResult.bind(this));
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
