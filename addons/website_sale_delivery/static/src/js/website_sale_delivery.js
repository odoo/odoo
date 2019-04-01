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
        // Workaround to:
        // - update the amount/error on the label at first rendering
        // - prevent clicking on 'Pay Now' if the shipper rating fails
        if ($carriers.length > 0) {
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
        $carrierInput.siblings('.o_wsale_delivery_badge_price').addClass('d-none');
        $carrierInput.siblings('.o_delivery_compute').removeClass('d-none').html('<span class="fa fa-spinner fa-spin"/>');
    },
    /**
     * @private
     * @param {Object} result
     */
    _handleCarrierUpdateResult: function (result) {
        this._handleCarrierUpdateResultBadge(result);
        var $payButton = $('#o_payment_form_pay');
        var $amountDelivery = $('#order_delivery span.oe_currency_value');
        var $amountUntaxed = $('#order_total_untaxed span.oe_currency_value');
        var $amountTax = $('#order_total_taxes span.oe_currency_value');
        var $amountTotal = $('#order_total span.oe_currency_value');

        if (result.status === true) {
            $amountDelivery.text(result.new_amount_delivery);
            $amountUntaxed.text(result.new_amount_untaxed);
            $amountTax.text(result.new_amount_tax);
            $amountTotal.text(result.new_amount_total);
            $payButton.data('disabled_reasons').carrier_selection = false;
            $payButton.prop('disabled', _.contains($payButton.data('disabled_reasons'), true));
        } else {
            $amountDelivery.text(result.new_amount_delivery);
            $amountUntaxed.text(result.new_amount_untaxed);
            $amountTax.text(result.new_amount_tax);
            $amountTotal.text(result.new_amount_total);
        }
    },
    /**
     * @private
     * @param {Object} result
     */
    _handleCarrierUpdateResultBadge: function (result) {
        var $carrierBadge = $('#delivery_carrier input[name="delivery_type"][value=' + result.carrier_id + '] ~ .badge.d-none');
        var $computeBadge = $('#delivery_carrier input[name="delivery_type"][value=' + result.carrier_id + '] ~ .o_delivery_compute');

        if (result.status === true) {
             // if free delivery (`free_over` field), show 'Free', not '$0'
             if (parseInt(result.new_amount_delivery)) {
                 $carrierBadge.children('span').text(result.new_amount_delivery);
             } else {
                 $carrierBadge.text(_t('Free'));
             }
             $carrierBadge.children('span').text(result.new_amount_delivery);
             $carrierBadge.removeClass('d-none');
             $computeBadge.addClass('d-none');
             $computeBadge.removeClass('o_wsale_delivery_carrier_error');
        } else {
            $computeBadge.addClass('o_wsale_delivery_carrier_error');
            $computeBadge.text(result.error_message);
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
        var $payButton = $('#o_payment_form_pay');
        $payButton.prop('disabled', true);
        $payButton.data('disabled_reasons', $payButton.data('disabled_reasons') || {});
        $payButton.data('disabled_reasons').carrier_selection = true;
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
