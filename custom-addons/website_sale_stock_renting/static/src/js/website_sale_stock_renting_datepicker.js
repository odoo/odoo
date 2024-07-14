/** @odoo-module **/

import { deserializeDateTime, serializeDateTime } from "@web/core/l10n/dates";
import WebsiteSaleDaterangePicker from '@website_sale_renting/js/website_sale_renting_daterangepicker';

WebsiteSaleDaterangePicker.include({
    events: Object.assign({}, WebsiteSaleDaterangePicker.prototype.events, {
        'change_product_id': '_onChangeProductId',
    }),
    rentingAvailabilities: {},

    /**
     * Override to get the renting product stock availabilities
     *
     * @override
     */
    willStart: function () {
        return Promise.all([
            this._super.apply(this, arguments),
            this._updateRentingProductAvailabilities(),
        ]);
    },

    // ------------------------------------------
    // Handlers
    // ------------------------------------------
    /**
     * Handle product changed to update the availabilities
     *
     * @param {Event} _event
     * @param {object} params
     */
    _onChangeProductId(_event, params) {
        if (this.productId !== params.product_id) {
            this.productId = params.product_id;
            this._updateRentingProductAvailabilities();
        }
    },

    // ------------------------------------------
    // Utils
    // ------------------------------------------
    /**
     * Update the renting availabilities dict with the unavailabilities of the current product
     *
     * @private
     */
    async _updateRentingProductAvailabilities() {
        const productId = this._getProductId();
        if (!productId || this.rentingAvailabilities[productId]) {
            return;
        }
        return this.rpc("/rental/product/availabilities", {
            product_id: productId,
            min_date: serializeDateTime(luxon.DateTime.now()),
            max_date: serializeDateTime(luxon.DateTime.now().plus({years: 3})),
        }).then((result) => {
            if (result.renting_availabilities) {
                result.renting_availabilities = result.renting_availabilities.map(
                    rentingAvailabilities => {
                        const {start, end, ...rest} = rentingAvailabilities;
                        return {
                            start: deserializeDateTime(start),
                            end: deserializeDateTime(end),
                            ...rest
                        }
                    }
                )
            }
            this.rentingAvailabilities[productId] = result.renting_availabilities || [];
            this.preparationTime = result.preparation_time;
            $('.oe_website_sale').trigger('renting_constraints_changed', {
                rentingAvailabilities: this.rentingAvailabilities,
                preparationTime: this.preparationTime,
            });
            this._verifyValidPeriod();
        });
    },

    /**
     * Set Custom CSS to a given daterangepicker cell
     *
     * This function is used in the daterange picker objects and meant to be easily overriden.
     *
     * @param {DateTime} date
     * @private
     */
    _isCustomDate(date) {
        const result = this._super.apply(this, arguments);
        const productId = this._getProductId();
        if (!productId) {
            return [];
        }
        const dateStart = date.startOf('day');
        for (const interval of this.rentingAvailabilities[productId]) {
            if (interval.start.startOf('day') > dateStart) {
                return result;
            }
            if (interval.end.endOf('day') > dateStart && interval.quantity_available <= 0) {
                result.push('o_daterangepicker_danger');
                return result;
            }
        }
        return result;
    },

    /**
     * Get the product id from the dom if not initialized.
     */
    _getProductId() {
        // cache this id a little bit ?
        this._super.apply(this, arguments);
        if (!this.productId) {
            const productSelector = [
                'input[type="hidden"][name="product_id"]',
                'input[type="radio"][name="product_id"]:checked'
            ];
            const form = this.el.closest('form');
            const productInput = form && form.querySelector(productSelector.join(', '));
            this.productId = productInput && parseInt(productInput.value);
        }
        return this.productId;
    },
});
