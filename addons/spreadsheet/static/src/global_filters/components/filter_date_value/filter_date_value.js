/** @odoo-module */

import { Component, onWillUpdateProps } from "@odoo/owl";
import { dateOptions } from "@spreadsheet/global_filters/helpers";
import { DateTimeInput } from "@web/core/datetime/datetime_input";

const { DateTime } = luxon;

export class DateFilterValue extends Component {
    setup() {
        this._setStateFromProps(this.props);
        onWillUpdateProps(this._setStateFromProps);
    }
    _setStateFromProps(props) {
        this.period = props.period;
        /** @type {number|undefined} */
        this.yearOffset = props.yearOffset;
        // date should be undefined if we don't have the yearOffset
        /** @type {DateTime|undefined} */
        this.date =
            this.yearOffset !== undefined
                ? DateTime.local().plus({ year: this.yearOffset })
                : undefined;
    }

    dateOptions(type) {
        return type ? dateOptions(type) : [];
    }

    isYear() {
        return this.props.type === "year";
    }

    isSelected(periodId) {
        return this.period === periodId;
    }

    /**
     * @param {Event & { target: HTMLSelectElement }} ev
     */
    onPeriodChanged(ev) {
        this.period = ev.target.value;
        this._updateFilter();
    }

    onYearChanged(date) {
        this.date = date;
        this.yearOffset = date.year - DateTime.now().year;
        this._updateFilter();
    }

    _updateFilter() {
        this.props.onTimeRangeChanged({
            yearOffset: this.yearOffset || 0,
            period: this.period,
        });
    }
}
DateFilterValue.template = "spreadsheet_edition.DateFilterValue";
DateFilterValue.components = { DateTimeInput };

DateFilterValue.props = {
    // See @spreadsheet_edition/bundle/global_filters/filters_plugin.RangeType
    type: { validate: (/**@type {string} */ t) => ["year", "month", "quarter"].includes(t) },
    onTimeRangeChanged: Function,
    yearOffset: { type: Number, optional: true },
    period: { type: String, optional: true },
};
