/** @odoo-module */

import { Component, onWillUpdateProps } from "@odoo/owl";
import { DateTimeInput } from "@web/core/datetime/datetime_input";
import { FILTER_DATE_OPTION, monthsOptions } from "@spreadsheet/assets_backend/constants";
import { getPeriodOptions } from "@web/search/utils/dates";

const { DateTime } = luxon;

export class DateFilterValue extends Component {
    setup() {
        this._setStateFromProps(this.props);
        onWillUpdateProps(this._setStateFromProps);
        this.dateOptions = this.getDateOptions();
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

    /**
     * Returns a list of time options to choose from according to the requested
     * type. Each option contains its (translated) description.
     * see getPeriodOptions
     *
     * @returns {Array<Object>}
     */
    getDateOptions() {
        const periodOptions = getPeriodOptions(DateTime.local());
        const quarters = FILTER_DATE_OPTION["quarter"].map((quarterId) =>
            periodOptions.find((option) => option.id === quarterId)
        );
        return quarters.concat(monthsOptions);
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
    onTimeRangeChanged: Function,
    yearOffset: { type: Number, optional: true },
    period: { type: String, optional: true },
};
