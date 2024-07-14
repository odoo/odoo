/** @odoo-module **/

import publicWidget from '@web/legacy/js/public/public_widget';
import { msecPerUnit, RentingMixin } from '@website_sale_renting/js/renting_mixin';
import { deserializeDateTime } from "@web/core/l10n/dates";

const { DateTime } = luxon;

publicWidget.registry.WebsiteSaleDaterangePicker = publicWidget.Widget.extend(RentingMixin, {
    selector: '.o_website_sale_daterange_picker',

    init() {
        this._super(...arguments);
        this.rpc = this.bindService("rpc");
    },

    /**
     * During start, load the renting constraints to validate renting pickup and return dates.
     *
     * @override
     */
    willStart() {
        return this._super.apply(this, arguments).then(() => {
            return this._loadRentingConstraints();
        });
    },

    /**
     * Start the website_sale daterange picker and save in the instance the value of the default
     * renting pickup and return dates, which could be undefined.
     *
     * @override
     */
    async start() {
        await this._super(...arguments);
        // Whether this is the daterange picker that is available on /shop/
        this.isShopDatePicker = this.el.classList.contains("o_website_sale_shop_daterange_picker");
        this.startDate = this._getDefaultRentingDate('start_date');
        this.endDate = this._getDefaultRentingDate('end_date');
        this.el.querySelectorAll(".o_daterange_picker").forEach((el) => {
            this._initSaleRentingDateRangePicker(el);
        });
        this._verifyValidPeriod();
    },

    /**
     * Checks if the default renting dates are set.
     * @returns {*}
     * @private
     */
    _hasDefaultDates() {
        return (this._getSearchDefaultRentingDate('start_date') && this._getSearchDefaultRentingDate('end_date'))
               ||
               (this.el.querySelector('input[name="default_start_date"]') && this.el.querySelector('input[name="default_end_date"]'));
    },

    /**
     * Load renting constraints.
     *
     * The constraints are the days where no pickup nor return can be processed and the minimal
     * duration of a renting.
     *
     * @private
     */
    async _loadRentingConstraints() {
        return this.rpc("/rental/product/constraints").then((constraints) => {
            this.rentingUnavailabilityDays = constraints.renting_unavailabity_days;
            this.rentingMinimalTime = constraints.renting_minimal_time;
            $('.oe_website_sale').trigger('renting_constraints_changed', {
                rentingUnavailabilityDays: this.rentingUnavailabilityDays,
                rentingMinimalTime: this.rentingMinimalTime,
            });
        });
    },

    /**
     * Initialize renting date input and attach to it a daterange picker object.
     *
     * A method is attached to the daterange picker in order to handle the changes.
     *
     * @param {HTMLElement} dateInput
     * @private
     */
    _initSaleRentingDateRangePicker(el) {
        const hasDefaultDates = Boolean(this._hasDefaultDates());
        el.dataset.hasDefaultDates = hasDefaultDates;
        const value =
            this.isShopDatePicker && !hasDefaultDates ? ["", ""] : [this.startDate, this.endDate];
        this.call(
            "datetime_picker",
            "create",
            {
                target: el,
                pickerProps: {
                    value,
                    range: true,
                    type: this._isDurationWithHours() ? "datetime" : "date",
                    minDate: DateTime.min(DateTime.now(), this.startDate),
                    maxDate: DateTime.max(DateTime.now().plus({ years: 3 }), this.endDate),
                    isDateValid: this._isValidDate.bind(this),
                    dayCellClass: (date) => this._isCustomDate(date).join(" "),
                },
                onApply: ([start_date, end_date]) => {
                    this.startDate = start_date;
                    this.endDate = end_date;
                    this._verifyValidPeriod();
                    this.$("input[name=renting_start_date]").change();
                    this.$el.trigger("daterangepicker_apply", {
                        start_date,
                        end_date,
                    });
                },
            },
            () => [
                el.querySelector("input[name=renting_start_date]"),
                el.querySelector("input[name=renting_end_date]"),
            ]
        ).enable();
    },

    // ------------------------------------------
    // Utils
    // ------------------------------------------
    /**
     * Get the default renting date from the hidden input filled server-side.
     *
     * @param {String} inputName - The name of the input tag that contains pickup or return date
     * @private
     */
    _getDefaultRentingDate(inputName) {
        let defaultDate = this._getSearchDefaultRentingDate(inputName);
        if (defaultDate) {
            return deserializeDateTime(defaultDate);
        }
        // that means that the date is not in the url
        const defaultDateEl = this.el.querySelector(`input[name="default_${inputName}"]`);
        if (defaultDateEl) {
            return deserializeDateTime(defaultDateEl.value);
        }
        if (this.startDate) {
            // that means that the start date is already set
            const rentingDurationMs = this.rentingMinimalTime.duration * msecPerUnit[this.rentingMinimalTime.unit];
            const defaultRentingDurationMs = msecPerUnit['day']; // default duration is 1 day
            let endDate = this.startDate.plus(
                Math.max(rentingDurationMs, defaultRentingDurationMs), 'ms'
            );
            return this._getFirstAvailableDate(endDate);
        }
        // that means that the date is not in the url and not in the hidden input
        // get the first available date based on this.rentingUnavailabilityDays
        let date = DateTime.now().plus({days: 1});
        return this._getFirstAvailableDate(date);
    },

    /**
     * Get the default renting date for the given input from the search params.
     *
     * @param {String} inputName - The name of the input tag that contains pickup or return date
     * @private
     */
    _getSearchDefaultRentingDate(inputName) {
        return new URLSearchParams(window.location.search).get(inputName);
    },

    /**
     * Check if the date is valid.
     *
     * This function is used in the daterange picker objects and meant to be easily overriden.
     *
     * @param {DateTime} date
     * @private
     */
    _isValidDate(date) {
        return !this.rentingUnavailabilityDays[date.weekday];
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
        return [];
    },

    /**
     * Verify that the dates given in the daterange picker are valid and display a message if not.
     *
     * @private
     */
    _verifyValidPeriod() {
        const message = this._getInvalidMessage(this.startDate, this.endDate, this._getProductId());
        if (message) {
            this.el.parentElement.querySelector('span[name=renting_warning_message]').innerText = message;
            this.el.parentElement.querySelector('.o_renting_warning').classList.remove('d-none');
            // only disable when there is a message. Hence, it doesn't override other disabling.
            $('.oe_website_sale').trigger('toggle_disable', [this._getParentElement(), !message]);
        } else {
            this.el.parentElement.querySelector('.o_renting_warning').classList.add('d-none');
        }
        this.el.dispatchEvent(new CustomEvent('toggle_search_btn', { bubbles: true, detail: message }));
        return !message;
    },

    _getProductId() {},

    _getParentElement() {
        return this.el.closest('form');
    },
    /**
     * Get the first available date based on this.rentingUnavailabilityDays.
     * @private
     */
    _getFirstAvailableDate(date) {
        let counter = 0;
        while (!this._isValidDate(date) && counter < 1000) {
            date = date.plus({days: 1});
            counter++;
        }
        return date;
    }
});

export default publicWidget.registry.WebsiteSaleDaterangePicker;
