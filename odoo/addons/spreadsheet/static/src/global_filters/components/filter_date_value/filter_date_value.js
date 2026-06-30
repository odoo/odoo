/** @odoo-module */

import { Component, onWillUpdateProps } from "@odoo/owl";
import { DateTimeInput } from "@web/core/datetime/datetime_input";
import { monthsOptions } from "@spreadsheet/assets_backend/constants";
import { QUARTER_OPTIONS } from "@web/search/utils/dates";

const { DateTime } = luxon;

export class DateFilterValue extends Component {
    static template = "spreadsheet_edition.DateFilterValue";
    static components = { DateTimeInput };
    static props = {
        // See @spreadsheet_edition/bundle/global_filters/filters_plugin.RangeType
        onTimeRangeChanged: Function,
        yearOffset: { type: Number, optional: true },
        period: { type: String, optional: true },
        disabledPeriods: { type: Array, optional: true },
    };
    setup() {
        this._setStateFromProps(this.props);
        this.dateOptions = this.getDateOptions(this.props);
        onWillUpdateProps((nextProps) => {
            this._setStateFromProps(nextProps);
            this.dateOptions = this.getDateOptions(nextProps);
        });
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
    getDateOptions(props) {
        const quarterOptions = Object.values(QUARTER_OPTIONS);
        const disabledPeriods = props.disabledPeriods || [];

        const dateOptions = [];
        if (!disabledPeriods.includes("quarter")) {
            dateOptions.push(...quarterOptions);
        }
        if (!disabledPeriods.includes("month")) {
            dateOptions.push(...monthsOptions);
        }
        return dateOptions;
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
