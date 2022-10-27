odoo.define('website_sale_delivery.checkout', function (require) {
'use strict';

var core = require('web.core');
var publicWidget = require('web.public.widget');

var _t = core._t;
var qweb = core.qweb;
var concurrency = require('web.concurrency');
var dp = new concurrency.DropPrevious();

publicWidget.registry.websiteSaleDelivery = publicWidget.Widget.extend({
    selector: '.oe_website_sale',
    events: {
        'change select[name="shipping_id"]': '_onSetAddress',
        'click .o_delivery_carrier_select': '_onCarrierClick',
        "click .o_address_select": "_onClickLocation",
        "click .o_remove_order_location": "_onClickRemoveLocation",
        "click .o_show_pickup_locations": "_onClickShowLocations",
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

        self._getCurrentLocation();

        _.each($carriers, async function (carrierInput, k) {
            self._showLoading($(carrierInput));
            const result = await self._rpc({
                route: '/shop/carrier_rate_shipment',
                params: {
                    'carrier_id': carrierInput.value,
                },
            })
            self._handleCarrierUpdateResult(result)
        });
        
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------
    /**
     * @private
     */
    _getCurrentLocation: async function () {
        const self=this;
        const data = await self._rpc({
            route: "/shop/access_point/get",
        })
        const order_locations = document.getElementsByClassName("o_order_location");
        for (const order_loc of order_locations) {
            const show_loc = order_loc.parentElement.nextElementSibling;
            // We could end not having the property
            let delivery_type=""
            if(order_loc.parentElement.parentElement.parentElement.children[0].attributes[8]){
                delivery_type = order_loc.parentElement.parentElement.parentElement.children[0].attributes[8].nodeValue;
            }
            if (!show_loc)
                continue;
            if (data[delivery_type+'_access_point']) {
                order_loc.innerText = data[delivery_type+'_access_point']
                order_loc.parentElement.classList.remove("d-none");
                show_loc.classList.add("d-none");
                break;
            } else {
                order_loc.parentElement.classList.add("d-none");
                show_loc.classList.remove("d-none");
            }
        }
    },

    /**
     * @private
     */
    _onClickRemoveLocation: async function (ev) {
        ev.stopPropagation();
        const self = this;
        await this._rpc({
            route: "/shop/access_point/set",
            params: {
                access_point_encoded: null,
            },
        })
        self._getCurrentLocation();
    },

    /**
     * @private
     * @param {Event} ev
     */
    _onClickShowLocations: async function (ev) {
        const self = this;
        const show_pickup_locations = ev.currentTarget;
        let modal = show_pickup_locations.nextElementSibling;
        if (!show_pickup_locations.getElementsByClassName("link-primary").length)
            return;
        const should_load_content = modal.firstChild ? false : true;
        while (modal.firstChild) {
            modal.lastChild.remove();
        }
        if (!should_load_content)
            return;

        var delivery_type = ev.currentTarget.closest(".o_delivery_carrier_select").childNodes[1].attributes[8].nodeValue;
        
        const delivery_type_id = ev.currentTarget.closest(".o_delivery_carrier_select").childNodes[1].value;
        await this._checkCarrier(ev,delivery_type_id)
        
        $(qweb.render(delivery_type + "_pickup_location_loading")).appendTo($(modal));
        const data = await self._rpc({
            route: "/shop/access_point/close_locations",
        })
        if (modal.firstChild)
            modal.firstChild.remove();
        if(!data || data && data.error || (data && data.close_locations && data.close_locations.length==0)){
            const error_message = document.createElement("em");
            error_message.classList.add("text-error");
            error_message.innerText = data.error ? data.error : "No available Pick-Up Locations";
            modal.appendChild(error_message);
            return;
        }
        
        var list_to_render = delivery_type + "_pickup_location_list";
        var data_to_render = {partner_address: data.partner_address};
        data_to_render[delivery_type+"_pickup_locations"] = data.close_locations;
        $(qweb.render(list_to_render, data_to_render)).appendTo($(modal));
        this._displayCarrierDropper(ev);  
    },
    /**
     * @private
     * @param {Object} obj // can be either an event or an objet returned by the controller
     */
    _displayCarrierDropper: async function (obj) {
        let current_id = obj.carrier_id
        const show_locations = document
            .getElementById("delivery_carrier")
            .getElementsByClassName("o_show_pickup_locations");

        // We check if it's an event
        if('currentTarget' in obj){
            const is_full_page_event = !obj.currentTarget.closest(".o_delivery_carrier_select")
            if(is_full_page_event)return;
            for (const show_loc of show_locations){
                this._specificDropperDisplay(show_loc);
            }
        }
        else{
            for (const show_loc of show_locations){
                const current_carrier_id = show_loc.closest("li").getElementsByTagName("input")[0].value;
                if (current_carrier_id == current_id) {
                    this._specificDropperDisplay(show_loc);
                    break;
                }
            }
        }
    },
    /**
     * @private
     * @param {Object} doc_carrier //carrier element from document
     */
    _specificDropperDisplay: function (doc_carrier) {
        if(!doc_carrier)
            return;
        if(!doc_carrier.closest("li").getElementsByTagName("input")[0].attributes[8])
            return;
        const current_carrier_type = doc_carrier.closest("li").getElementsByTagName("input")[0].attributes[8].nodeValue;
        const location_still_loading = document.getElementById("#"+current_carrier_type+"_addresses")
        if(location_still_loading)return
        while (doc_carrier.firstChild) {
            doc_carrier.lastChild.remove();
        }
        const current_carrier_checked = doc_carrier.closest("li").getElementsByTagName("input")[0].checked;
        const span = document.createElement("em");
        const is_pick_up_location_list = doc_carrier.nextElementSibling.childNodes.length > 0
        if(current_carrier_checked){
            const chevron_down = document.createElement("i");
            if(is_pick_up_location_list)
                chevron_down.classList.add("fa", "fa-angle-up");
            else
                chevron_down.classList.add("fa", "fa-angle-down");
            span.textContent = "Pick-Up Locations ";
            span.classList.add("link-primary");
            span.appendChild(chevron_down);
        }
        else {
            span.textContent = "select to see available Pick-Up Locations";
            span.classList.add("text-muted");
        }
        doc_carrier.appendChild(span);
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onClickLocation: async function (ev) {
        ev.preventDefault();
        const carrierId = ev.currentTarget.closest(".o_delivery_carrier_select").childNodes[1].value;
        await this._checkCarrier(ev,carrierId)
        const self = this;
        const modal = ev.target.closest(".o_list_pickup_locations");
        const encoded_location = ev.target.previousElementSibling.innerText;
        await self._rpc({
            route: "/shop/access_point/set",
            params: {
                access_point_encoded: encoded_location,
            },
        })
        while (modal.firstChild) {
            modal.lastChild.remove();
        }
        self._getCurrentLocation();
    },
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

        var $carriers_inputs = $('#delivery_carrier input[name="delivery_type"]');
        var carriers = [];
        _.each($carriers_inputs, function (carrierInput, k) {
            carriers.push(carrierInput.dataset.deliveryType);
        })
        this._displayCarrierDropper(result);       
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
    _onCarrierClick: async function (ev) {
        var $radio = $(ev.currentTarget).find('input[type="radio"]');
        this._showLoading($radio);
        $radio.prop("checked", true);
        var $payButton = $('button[name="o_payment_submit_button"]');
        $payButton.prop('disabled', true);
        var disabledReasons = $payButton.data('disabled_reasons') || {};
        disabledReasons.carrier_selection = true;
        $payButton.data('disabled_reasons', disabledReasons);
        const data = await dp.add(this._rpc({
            route: '/shop/update_carrier',
            params: {
                carrier_id: $radio.val(),
            },
        }))
        this._handleCarrierUpdateResult(data);
    },

    _checkCarrier: async function (ev, carrier_id) {
        ev.stopPropagation();
        await dp.add(this._rpc({
            route: '/shop/update_carrier',
            params: {
                carrier_id: carrier_id,
            },
        }))
        var closestDocElement = ev.currentTarget.closest('.o_delivery_carrier_select');
        var $radio = $(closestDocElement).find('input[type="radio"]');
        $radio.prop("checked", true);
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
