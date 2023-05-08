/** @odoo-module alias=website_sale_delivery.checkout **/

import core from "web.core";
import publicWidget from "web.public.widget";

const _t = core._t;
const qweb = core.qweb;
import concurrency from "web.concurrency";

publicWidget.registry.websiteSaleDelivery = publicWidget.Widget.extend({
    selector: '.oe_website_sale',
    events: {
        'change select[name="shipping_id"]': '_onSetAddress',
        'click .o_delivery_carrier_select': '_onCarrierClick',
        "click .o_address_select": "_onClickLocation",
        "click .o_remove_order_location": "_onClickRemoveLocation",
        "click .o_show_pickup_locations": "_onClickShowLocations",
        "click .o_payment_option_card": "_onClickPaymentMethod"
    },

    /**
     * @override
     */
    start: async function () {
        const carriers = Array.from(document.querySelectorAll('input[name="delivery_type"]'));
        this.dp = new concurrency.DropPrevious();
        // Workaround to:
        // - update the amount/error on the label at first rendering
        // - prevent clicking on 'Pay Now' if the shipper rating fails
        if (carriers.length > 0) {
            const carrierChecked = carriers.filter(e =>e.checked)
            if (carrierChecked.length === 0) {
                const payButton = document.querySelector('button[name="o_payment_submit_button"]');
                payButton? payButton.disabled = true : null;
            } else {
                carrierChecked[0].click();
            }
        }

        await this._getCurrentLocation();
        await carriers.forEach(async (carrierInput) => {
            this._showLoading((carrierInput));
            await this._handleCarrierUpdateResult(carrierInput)
        });
        if (this._super && typeof(this._super.apply)==="function") {
          return this._super.apply(this, arguments);
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------
    /**
     * @private
     */
    _getCurrentLocation: async function () {
        const data = await this._rpc({
            route: "/shop/access_point/get",
        })
        const carriers = document.querySelectorAll('.o_delivery_carrier_select')
        for (let carrier of carriers) {
            const deliveryType = carrier.querySelector('input[type="radio"]').getAttribute("delivery_type");
            const deliveryName = carrier.querySelector('label').innerText;
            const showLoc = carrier.querySelector(".o_show_pickup_locations");
            if (!showLoc) {
                continue;
            }
            const orderLoc = carrier.querySelector(".o_order_location");
            if (data[deliveryType + '_access_point'] && data.delivery_name == deliveryName) {
                orderLoc.querySelector(".o_order_location_name").innerText = data.name
                orderLoc.querySelector(".o_order_location_address").innerText = data[deliveryType + '_access_point']
                orderLoc.parentElement.classList.remove("d-none");
                showLoc.classList.add("d-none");
                break;
            } else {
                orderLoc.parentElement.classList.add("d-none");
                showLoc.classList.remove("d-none");
            }
        }
    },

    /**
     * @private
     * @param {Element} docCarrier //carrier element from document
     */
    _specificDropperDisplay: function (docCarrier) {
        if(!docCarrier?.closest("li").getElementsByTagName("input")[0].getAttribute("delivery_type")){
            return;
        }
        while (docCarrier.firstChild) {
            docCarrier.lastChild.remove();
        }
        const currentCarrierChecked = docCarrier.closest("li").getElementsByTagName("input")[0].checked;
        const span = document.createElement("em");
        if (!currentCarrierChecked) {
            span.textContent = "select to see available Pick-Up Locations";
            span.classList.add("text-muted");
        }
        docCarrier.appendChild(span);
    },
    /**
     * @private
     * @param {Element} carrierInput
     */
    _showLoading: function (carrierInput) {
        const priceTag = carrierInput.parentNode.querySelector('.o_wsale_delivery_badge_price')
        while (priceTag.firstChild) {
            priceTag.removeChild(priceTag.lastChild);
        }
        const loadingCircle = priceTag.appendChild(document.createElement('span'));
        loadingCircle.classList.add("fa", "fa-circle-o-notch", "fa-spin");
    },
    /**
     * Update the total cost according to the selected shipping method
     *
     * @private
     * @param {float} amount : The new total amount of to be paid
     */
    _updateShippingCost: function(amount) {
        core.bus.trigger('update_shipping_cost', amount);
    },
    /**
     * @private
     * @param {Object} result
     */
    _handleCarrierUpdateResult: async function (carrierInput) {
        const result = await this._rpc({
            route: '/shop/update_carrier',
            params: {
                'carrier_id': carrierInput.value,
            },
        })
        this._handleCarrierUpdateResultBadge(result);
        if (carrierInput.checked) {
            var amountDelivery = document.querySelector('#order_delivery .monetary_field');
            var amountUntaxed = document.querySelector('#order_total_untaxed .monetary_field');
            var amountTax = document.querySelector('#order_total_taxes .monetary_field');
            var amountTotal = document.querySelectorAll('#order_total .monetary_field, #amount_total_summary.monetary_field');

            amountDelivery.innerHTML = result.new_amount_delivery;
            amountUntaxed.innerHTML = result.new_amount_untaxed;
            amountTax.innerHTML = result.new_amount_tax;
            amountTotal.forEach(total => total.innerHTML = result.new_amount_total);
            // we need to check if it's the carrier that is selected
            if (result.new_amount_total_raw !== undefined) {
                this._updateShippingCost(result.new_amount_total_raw);
            }
            this._updateShippingCost(result.new_amount_delivery);
        }
        this._setIsPayable(result.status);
        let currentId = result.carrier_id
        const showLocations = document.querySelectorAll(".o_show_pickup_locations");

        for (const showLoc of showLocations) {
            const currentCarrierId = showLoc.closest("li").getElementsByTagName("input")[0].value;
            if (currentCarrierId == currentId) {
                this._specificDropperDisplay(showLoc);
                break;
            }
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

    _disablePayButtonNoPickupPoint : function (ev){
        const selectedCarrierEl = ev.currentTarget.closest('.o_delivery_carrier_select');
        const address = selectedCarrierEl.querySelector('.o_order_location_address').innerText
        const isPickUp = selectedCarrierEl.lastChild.previousSibling.children;

        document.querySelectorAll('.error_no_pick_up_point').forEach(el => el.remove());

        if (isPickUp.length > 1 && (address == "" || isPickUp[0].classList.contains("d-none"))) {
            var payButton = document.querySelector('button[name="o_payment_submit_button"]');
            payButton? payButton.disabled = true : null;
            const errorNode = document.createElement("i");
            errorNode.classList.add("small", "error_no_pick_up_point","ms-2");
            errorNode.textContent = _t("Select a pick-up point");
            errorNode.style = "color:red;";
            selectedCarrierEl.insertBefore(errorNode, selectedCarrierEl.querySelector("label").nextElementSibling);
        }
    },

    _checkCarrier: async function (ev, carrier_id) {
        ev.stopPropagation();
        await this.dp.add(this._rpc({
            route: '/shop/update_carrier',
            params: {
                carrier_id: carrier_id,
            },
        }))
        var closestDocElement = ev.currentTarget.closest('.o_delivery_carrier_select');
        var radio = closestDocElement.querySelector('input[type="radio"]');
        radio.checked = true;
        this._disablePayButtonNoPickupPoint(ev)
    },

    _onClickPaymentMethod: async function (ev) {
        const carriers = Array.from(document.querySelectorAll('.o_delivery_carrier_select'))
        let carrierChecked = null;
        carriers.forEach((carrier) => {
            if (carrier.querySelector('input').checked){
                carrierChecked = carrier;
            }
        })
        if (!carrierChecked) {
            return;
        }
        const carrier_id = carrierChecked?.querySelector('input')?.value;
        const result = await this._rpc({
            route: '/shop/update_carrier',
            params: {
                'carrier_id': carrier_id,
            },
        })
        this._setIsPayable(result.status)
    },
    /**
     * @private
     * @param {boolean} status  : the status of the rate_shipment request
     */
    // FYI we don't cover the case where the payement method is not selected because it already throws an error
    _setIsPayable: function(status=false){
        // abort if no paybutton
        var payButton = document.querySelector('button[name="o_payment_submit_button"]');
        if (!payButton) {
            return;
        }
        // abort if the rating failed
        if (!status){
            payButton.disabled = true;
            return;
        }
        const carriers = Array.from(document.querySelectorAll('.o_delivery_carrier_select'))
        let carrierChecked = null;
        carriers.forEach((carrier) => {
            if (carrier.querySelector('input').checked){
                carrierChecked = carrier;
            }
        })
        //abort if no carrier is selected
        if (!carrierChecked){
            payButton.disabled = true;
            return;
        }

        // if the carrier does not need a pickup point
        const isPickUpPointNeeded = carrierChecked.querySelector('.o_show_pickup_locations')
        if (!isPickUpPointNeeded){
            payButton.disabled = false;
            return;
        }

        const address = carrierChecked.querySelector('.o_order_location_address').innerText
        const isPickUp = carrierChecked.lastChild.previousSibling.children;
        if (isPickUp.length > 1 && (address == "" || isPickUp[0].classList.contains("d-none"))) {
            payButton.disabled = true ;
            return
        }
        payButton.disabled = false;
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onClickRemoveLocation: async function (ev) {
        ev.stopPropagation();
        await this._rpc({
            route: "/shop/access_point/set",
            params: {
                access_point_encoded: null,
            },
        })
        const deliveryTypeInput = ev.currentTarget.closest(".o_delivery_carrier_select").querySelector('input[name="delivery_type"]');
        const deliveryTypeId = deliveryTypeInput.value;
        await Promise.all([this._getCurrentLocation(),this._checkCarrier(ev,deliveryTypeId)])
        await this._onClickShowLocations(ev);
    },

    /**
     * @private
     * @param {Event} ev
     */
    _onClickShowLocations: async function (ev) {
        // This checks if there is a pick up point already select with that carrier
        if (!ev.currentTarget.closest('.o_delivery_carrier_select').querySelector(".o_order_location").parentElement.classList.contains("d-none")) {
            return;
        }
        const showPickupLocations = ev.currentTarget.closest('.o_delivery_carrier_select').querySelector('.o_show_pickup_locations');
        const modal = showPickupLocations?.nextElementSibling;
        if (!modal) {
            return;
        }

        while (modal.firstChild) {
            modal.lastChild.remove();
        }
        const deliveryTypeInput = ev.currentTarget.closest(".o_delivery_carrier_select").querySelector('input[name="delivery_type"]');
        const deliveryType = deliveryTypeInput.getAttribute("delivery_type");
        const deliveryTypeId = deliveryTypeInput.value;
        await this._checkCarrier(ev,deliveryTypeId)
        $(qweb.render(deliveryType + "_pickup_location_loading")).appendTo($(modal));
        const data = await this._rpc({
            route: "/shop/access_point/close_locations",
        })
        if (modal.firstChild){
            modal.firstChild.remove();
        }
        if (data.error || (data.close_locations.length === 0)) {
            const errorMessage = document.createElement("em");
            errorMessage.classList.add("text-error");
            errorMessage.innerText = data.error ? data.error : "No available Pick-Up Locations";
            modal.appendChild(errorMessage);
            return;
        }

        var listToRender = deliveryType + "_pickup_location_list";
        var dataToRender = {partner_address: data.partner_address};
        dataToRender[deliveryType + "_pickup_locations"] = data.close_locations;
        $(qweb.render(listToRender, dataToRender)).appendTo($(modal));

        const showLocations = document.querySelectorAll(".o_show_pickup_locations");
        if (!ev.currentTarget.closest(".o_delivery_carrier_select")) {
            return;
        }
        for (const showLoc of showLocations) {
            this._specificDropperDisplay(showLoc);
        }
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onCarrierClick: async function (ev) {
        const radio = ev.currentTarget.closest('.o_delivery_carrier_select').querySelector('input[type="radio"]');
        if (radio.checked) {
            return;
        }
        this._showLoading(radio);
        radio.checked = true;
        await this._onClickShowLocations(ev);
        await this._handleCarrierUpdateResult(radio);
        this._disablePayButtonNoPickupPoint(ev);
    },

    /**
     * @private
     * @param {Event} ev
     */
    _onClickLocation: async function (ev) {
        const carrierId = ev.currentTarget.closest(".o_delivery_carrier_select").childNodes[1].value;
        await this._checkCarrier(ev,carrierId)
        const modal = ev.target.closest(".o_list_pickup_locations");
        const encodedLocation = ev.target.previousElementSibling.innerText;
        await this._rpc({
            route: "/shop/access_point/set",
            params: {
                access_point_encoded: encodedLocation,
            },
        })
        while (modal.firstChild) {
            modal.lastChild.remove();
        }
        await this._getCurrentLocation();
        document.querySelectorAll('.error_no_pick_up_point').forEach(el => el.remove());
        const result = await this._rpc({
            route: '/shop/update_carrier',
            params: {
                'carrier_id': carrierId,
            },
        })
        this._setIsPayable(result.status)
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
