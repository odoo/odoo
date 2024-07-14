/** @odoo-module **/

import { serializeDateTime, deserializeDateTime, parseDateTime, ConversionError, parseDate } from "@web/core/l10n/dates";
import { sprintf } from "@web/core/utils/strings";
import { _t } from "@web/core/l10n/translation";

export const msecPerUnit = {
    hour: 3600 * 1000,
    day: 3600 * 1000 * 24,
    week: 3600 * 1000 * 24 * 7,
    month: 3600 * 1000 * 24 * 30,
};
export const unitMessages = {
    hour: _t("(%s hours)."),
    day: _t("(%s days)."),
    week: _t("(%s weeks)."),
    month: _t("(%s months)."),
};

export const RentingMixin = {
    /**
     * Get the message to display if the renting has invalid dates.
     *
     * @param {DateTime} startDate
     * @param {DateTime} endDate
     * @private
     */
    _getInvalidMessage(startDate, endDate, productId = false) {
        let message;
        if (!this.rentingUnavailabilityDays || !this.rentingMinimalTime) {
            return message;
        }
        if (startDate && endDate) {
            if (this.rentingUnavailabilityDays[startDate.weekday]) {
                message = _t("You cannot pick up your rental on that day of the week.");
            } else if (this.rentingUnavailabilityDays[endDate.weekday]) {
                message = _t("You cannot return your rental on that day of the week.");
            } else {
                const rentingDuration = endDate - startDate;
                if (rentingDuration < 0) {
                    message = _t("The return date should be after the pickup date.");
                } else if (startDate.startOf("day") < luxon.DateTime.now().startOf("day")) {
                    message = _t("The pickup date cannot be in the past.");
                } else if (
                    ["hour", "day", "week", "month"].includes(this.rentingMinimalTime.unit)
                ) {
                    const unit = this.rentingMinimalTime.unit;
                    if (rentingDuration / msecPerUnit[unit] < this.rentingMinimalTime.duration) {
                        message = _t(
                            "The rental lasts less than the minimal rental duration %s",
                            sprintf(unitMessages[unit], this.rentingMinimalTime.duration)
                        );
                    }
                }
            }
        } else {
            message = _t("Please select a rental period.");
        }
        return message;
    },

    _isDurationWithHours() {
        if (
            this.rentingMinimalTime &&
            this.rentingMinimalTime.duration > 0 &&
            this.rentingMinimalTime.unit !== "hour"
        ) {
            return false;
        }
        const unitInput = this.el.querySelector("input[name=rental_duration_unit]");
        return unitInput && unitInput.value === "hour";
    },

    /**
     * Get the date from the daterange input or the default
     *
     * @private
     */
    _getDateFromInputOrDefault(input, fieldName, inputName) {
        const parse = this._isDurationWithHours() ? parseDateTime : parseDate;
        try {
            return parse(input?.value);
        } catch (e) {
            if (!(e instanceof ConversionError)) {
                throw e;
            }
            const $defaultDate = this.el.querySelector('input[name="default_' + inputName + '"]');
            return $defaultDate && deserializeDateTime($defaultDate.value);
        }
    },

    /**
     * Get the renting pickup and return dates from the website sale renting daterange picker object.
     *
     * @private
     * @param {$.Element} $product
     */
    _getRentingDates($product) {
        const [startDate] = ($product || this.$el).find("input[name=renting_start_date]");
        const [endDate] = ($product || this.$el).find("input[name=renting_end_date]");
        if (startDate || endDate) {
            let startDateValue = this._getDateFromInputOrDefault(startDate, "startDate", "start_date");
            let endDateValue = this._getDateFromInputOrDefault(endDate, "endDate", "end_date");
            if (startDateValue && endDateValue && !this._isDurationWithHours()) {
                startDateValue = startDateValue.startOf('day');
                endDateValue = endDateValue.endOf('day');
            }
            return {
                start_date: startDateValue,
                end_date: endDateValue,
            };
        }
        return {};
    },

    /**
     * Return serialized dates from `_getRentingDates`. Used for client-server exchange.
     *
     * @private
     * @param {$.Element} $product
     */
    _getSerializedRentingDates($product) {
        const { start_date, end_date } = this._getRentingDates($product);
        if (start_date && end_date) {
            return {
                start_date: serializeDateTime(start_date),
                end_date: serializeDateTime(end_date),
            };
        }
    },
};
