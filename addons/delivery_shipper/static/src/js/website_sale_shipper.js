/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import "@website_sale/js/website_sale_delivery";
import { renderToElement } from "@web/core/utils/render";

const WebsiteSaleDeliveryWidget = publicWidget.registry.websiteSaleDelivery;

WebsiteSaleDeliveryWidget.include({
    events: Object.assign({
        "click #btn_confirm_shipper": "_onClickBtnConfirmShipper",
    }, WebsiteSaleDeliveryWidget.prototype.events),

    /**
     * Loads Shipper modal the first time, else show it.
     *
     * @override
     */
    _handleCarrierUpdateResult: async function (carrierInput) {
        await this._super(...arguments);
        console.log(this.result)
        if (this.result.is_shipper) {
                // this._loadShipperModal(this.result);
                // this._populateShipperRates(this.result.shipper_rates);
                // //this.$modal_mondialrelay.find('#btn_confirm_relay').toggleClass('disabled', !this.result.mondial_relay.current);
                // this.$modal_shipper.modal('show');
            
            // TODO: Weird, first time clicking to it always doesn't show the modal, must be the second time
            if (this.result.is_shipper) {
                if (!$('#modal_shipper').length) {
                    this._loadShipperModal(this.result);
                    this._populateShipperRates(this.result.shipper_rates);
                } else {
                    this.$modal_shipper.modal('show');
                }
            }
        }
    },
    /**
     * @private
     *
     * @param {Object} result: dict returned by call of _update_website_sale_delivery_return (python)
     */
    _loadShipperModal: function (result) {
        $(renderToElement('website_sale_shipper', {})).appendTo('body');
        this.$modal_shipper = $('#modal_shipper');
        this.$modal_shipper.find('#btn_confirm_shipper').on('click', this._onClickBtnConfirmShipper.bind(this));
    },

    /**
     * Populate shipping rates into the modal-body.
     * 
     * @private
     * @param {Array} rates Array of shipping rate objects.
     */
    _populateShipperRates: function (rates) {
        const ratesHtml = rates.map(rate => `
            <div class="rate-option" 
                data-rate-id="${rate.rate_id}" 
                data-rate-name="${rate.carrier_name}" 
                data-rate-price="${rate.final_price}">
                <p>
                    <strong>${rate.carrier_name}</strong> - 
                    ${rate.service}: ${rate.final_price} 
                    (<span>${rate.delivery_time}</span>)
                </p>
            </div>
        `).join("");

        this.$modal_shipper.find('.modal-body').html(`
            <div class="rate-options">
                ${ratesHtml}
            </div>
        `);

        // Event handling for selecting a rate
        this.$modal_shipper.find('.rate-option').on('click', (ev) => {
            this.$modal_shipper.find('.rate-option').removeClass('selected');
            $(ev.currentTarget).addClass('selected');
            this.$modal_shipper.find('#btn_confirm_shipper').removeClass('disabled');
        });
    },
    /**
     * Update the shipping address on the order and refresh the UI.
     *
     * @private
     *
     */
    _onClickBtnConfirmShipper: function () {
        const selectedRate = this.$modal_shipper.find('.rate-option.selected');
        if (!selectedRate.length) {
            alert("Please select a shipping rate.");
            return;
        }
    
        const rateId = selectedRate.data('rate-id');
        const ratePrice = selectedRate.data('rate-price');
        const rateName = selectedRate.data('rate-name');
        console.log(rateId)
        console.log(ratePrice)
        console.log(rateName)

        this._updateShippingCost(ratePrice);
    
    },
});
