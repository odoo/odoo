/** @odoo-module **/

import { WebsiteSale } from '@website_sale/js/website_sale';
import { RentingMixin } from '@website_sale_renting/js/renting_mixin';
import wSaleUtils from "@website_sale/js/website_sale_utils";
import '@website_sale_renting/js/variant_mixin';
import {
    deserializeDateTime,
    serializeDateTime,
    formatDate,
    formatDateTime,
} from "@web/core/l10n/dates";

WebsiteSale.include(RentingMixin);
WebsiteSale.include({
    events: Object.assign(WebsiteSale.prototype.events, {
        'renting_constraints_changed': '_onRentingConstraintsChanged',
        'toggle_disable': '_onToggleDisable',
        'change .js_main_product .o_website_sale_daterange_picker': 'onChangeVariant',
        'daterangepicker_apply': '_onDatePickerApply',
        'click .clear-daterange': '_onDatePickerClear',
    }),

    async _check_new_dates_on_cart(){
        const { start_date, end_date, values } = await this.rpc(
            '/shop/cart/update_renting',
            this._getSerializedRentingDates()
        );
        wSaleUtils.updateCartNavBar(values);
        const format = this._isDurationWithHours() ? formatDateTime : formatDate;
        document.querySelector("input[name=renting_start_date]").value = format(deserializeDateTime(start_date));
        document.querySelector("input[name=renting_end_date]").value = format(deserializeDateTime(end_date));
    },

    /**
     * Assign the renting dates to the rootProduct for rental products.
     *
     * @override
     */
    _updateRootProduct($form, productId) {
        this._super(...arguments);
        Object.assign(this.rootProduct, this._getSerializedRentingDates());
    },

    // ------------------------------------------
    // Handlers
    // ------------------------------------------
    /**
     * During click, verify the renting periods
     *
     * @private
     * @returns {Promise} never resolved
     */
    _onClickAdd(ev) {
        const $form = this.$(ev.currentTarget).closest('form');
        if ($form.find('input[name="is_rental"]').val()) {
            if (!this._verifyValidRentingPeriod($form)) {
                ev.stopPropagation();
                return Promise.resolve();
            }
        }

        return this._super(...arguments);
    },

    /**
     * Update the instance value when the renting constraints changes.
     *
     * @param {Event} _event
     * @param {object} info
     */
    _onRentingConstraintsChanged(_event, info) {
        if (info.rentingUnavailabilityDays) {
            this.rentingUnavailabilityDays = info.rentingUnavailabilityDays;
        }
        if (info.rentingMinimalTime) {
            this.rentingMinimalTime = info.rentingMinimalTime;
        }
    },

    /**
     * Handler to call the function which toggles the disabled class
     * depending on the $parent element and the availability of the current combination.
     *
     * @param {Event} _event event
     * @param {HTMLElement} parent parent element
     * @param {Boolean} isCombinationAvailable whether the combination is available
     */
    _onToggleDisable(_event, parent, isCombinationAvailable) {
        this._toggleDisable($(parent), isCombinationAvailable);
    },

    // ------------------------------------------
    // Utils
    // ------------------------------------------

    /**
     * Verify that the dates given in the daterange picker are valid and display a message if not.
     *
     * @param {JQuery} $parent
     * @private
     */
    _verifyValidRentingPeriod($parent) {
        const rentingDates = this._getRentingDates();
        if (!this._verifyValidInput(rentingDates, 'start_date') ||
            !this._verifyValidInput(rentingDates, 'end_date')) {
            return false;
        }
        const message = this._getInvalidMessage(
            rentingDates.start_date, rentingDates.end_date,
            this._getProductId($parent.closest('form'))
        );
        if (message) {
            this.el.querySelector('span[name=renting_warning_message]').innerText = message;
            this.el.querySelector('.o_renting_warning').classList.remove('d-none');
            // only disable when there is a message. Hence, it doesn't override other disabling.
            this._toggleDisable($parent.closest('form'), !message);
        } else {
            this.el.querySelector('.o_renting_warning').classList.add('d-none');
        }
        return !message;
    },

    /**
     * Verify the renting date extracted from input is valid.
     *
     * @param {object} rentingDates
     * @param {string} inputName
     */
    _verifyValidInput(rentingDates, inputName) {
        const input = this.el.querySelector('input[name=renting_' + inputName + ']');
        if (input) {
            input.classList.toggle('is-invalid', !rentingDates[inputName]);
        }
        return rentingDates[inputName];
    },

    /**
     * Verify the Renting Period on combination change.
     *
     * @param {Event} ev
     * @param {JQueryElement} $parent
     * @param {Object} combination
     * @returns
     */
    _onChangeCombination(ev, $parent, combination) {
        const result = this._super.apply(this, arguments);
        this._verifyValidRentingPeriod($parent);
        return result;
    },

    _onDatePickerApply: function (ev, { start_date, end_date }) {
        if (document.querySelector(".oe_cart")) {
            if (start_date && end_date) {
                this._check_new_dates_on_cart();
            }
        } else if (document.querySelector(".o_website_sale_shop_daterange_picker")) {
            this._addDatesToQuery(start_date, end_date);
        }
    },
    /**
     * Redirect to the shop page with the appropriate dates as search params.
     */
    _addDatesToQuery(start_date, end_date) {
        // get current URL parameters
        const searchParams = new URLSearchParams(window.location.search);
        if (start_date && end_date) {
            searchParams.set("start_date", serializeDateTime(start_date));
            searchParams.set("end_date", serializeDateTime(end_date));
        }
        window.location = `/shop?${searchParams}`;
        this.isRedirecting = true;
    },

    _onDatePickerClear: function (ev) {
        const searchParams = new URLSearchParams(window.location.search);
        searchParams.delete('start_date');
        searchParams.delete('end_date');
        const searchString = searchParams.toString();
        window.location = `${window.location.pathname}` + searchString.length ? `?${searchParams.toString()}` : ``;
    },
});
