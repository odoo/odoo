/** @ts-check */

import { Component, onWillUpdateProps } from "@odoo/owl";
import { DateTimeInput } from "@web/core/datetime/datetime_input";
import { _t } from "@web/core/l10n/translation";

const { DateTime } = luxon;

/**
 * @typedef {Object} DateOption
 * @property {string} id
 * @property {string | import("@spreadsheet").LazyTranslatedString} description
 */

function getQuarterList() {
    return Array.from({ length: 4 }, (_, i) => ({
        id: `quarter_${i + 1}`,
        description: _t("Q%(quarter_number)s", {
            quarter_number: i + 1,
        }),
    }));
}

function getMonthList() {
    return Array.from({ length: 12 }, (_, i) => ({
        id: `month_${i + 1}`,
        description: DateTime.local()
            .set({ month: i + 1 })
            .toFormat("LLLL"),
    }));
}

export class DateFilterValue extends Component {
    static template = "spreadsheet.DateFilterValue";
    static components = { DateTimeInput };
    static props = {
        // See @spreadsheet/bundle/global_filters/filters_plugin.RangeType
        onTimeRangeChanged: Function,
        value: { type: Object, optional: true },
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
        this.value = props.value;
        if (!this.value) {
            this.value = {
                type: "year",
                period: {
                    year: undefined,
                },
            };
        }
        /** @type {number|undefined} */
        // date should be undefined if we don't have the year
        this.date =
            this.value.period.year !== undefined
                ? DateTime.local().set({ year: this.value.period.year })
                : undefined;
        this.selectedPeriodId = undefined;
        switch (this.value.type) {
            case "quarter":
                this.selectedPeriodId = `quarter_${this.value.period.quarter}`;
                break;
            case "month":
                this.selectedPeriodId = `month_${this.value.period.month}`;
                break;
        }
    }

    /**
     * Returns a list of time options to choose from according to the requested
     * type. Each option contains its (translated) description.
     *
     * @returns {Array<Object>}
     */
    getDateOptions(props) {
        const disabledPeriods = props.disabledPeriods || [];

        const dateOptions = [];
        if (!disabledPeriods.includes("quarter")) {
            dateOptions.push(...getQuarterList());
        }
        if (!disabledPeriods.includes("month")) {
            dateOptions.push(...getMonthList());
        }
        return dateOptions;
    }

    isSelected(periodId) {
        return this.selectedPeriodId === periodId;
    }

    /**
     * @param {Event & { target: HTMLSelectElement }} ev
     */
    onPeriodChanged(ev) {
        const value = ev.target.value;
        if (value.startsWith("month_")) {
            this.value = {
                type: "month",
                period: {
                    year: this.value.period.year || DateTime.local().year,
                    month: Number.parseInt(value.replace("month_", ""), 10),
                },
            };
        } else {
            this.value = {
                type: "quarter",
                period: {
                    year: this.value.period.year || DateTime.local().year,
                    quarter: Number.parseInt(value.replace("quarter_", ""), 10),
                },
            };
        }
        this._updateFilter();
    }

    onYearChanged(date) {
        this.date = date;
        this.value = {
            type: this.value.type,
            period: {
                ...this.value.period,
                year: date.year,
            },
        };
        this._updateFilter();
    }

    _updateFilter() {
        this.props.onTimeRangeChanged(this.value);
    }
}
