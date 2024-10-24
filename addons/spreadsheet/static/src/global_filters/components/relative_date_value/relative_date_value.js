/** @ts-check */

import {
    RELATIVE_DATE_RANGE_REFERENCES,
    RELATIVE_DATE_RANGE_UNITS,
} from "@spreadsheet/helpers/constants";
import { getRelativeDateInterval } from "@spreadsheet/global_filters/relative_date_helpers";

import { Component } from "@odoo/owl";

const { DateTime } = luxon;

export class RelativeDateValue extends Component {
    static template = "spreadsheet_edition.RelativeDateValue";
    static components = {};
    static props = {
        value: { type: Object, optional: true },
        onChange: Function,
    };

    setup() {
        super.setup();
        this.relativeDateRangesUnits = RELATIVE_DATE_RANGE_UNITS;
        this.relativeDateRangesReferences = RELATIVE_DATE_RANGE_REFERENCES;
    }

    get defaultValue() {
        return { reference: "this", unit: "month" };
    }

    get inputIntervalValue() {
        if (!this.props.value || this.props.value.reference === "this") {
            return undefined;
        }
        return this.props.value.interval || 1;
    }

    get computedDate() {
        if (!this.props.value) {
            return undefined;
        }
        return getRelativeDateInterval(DateTime.local(), this.props.value, 0).toLocaleString(
            DateTime.DATE_MED
        );
    }

    onReferenceChanged(ev) {
        if (ev.target.value === "") {
            this.props.onChange(undefined);
            return;
        }
        this.props.onChange({
            ...this.defaultValue,
            ...this.props.value,
            reference: ev.target.value,
        });
    }

    onUnitChanged(ev) {
        this.props.onChange({
            ...this.defaultValue,
            ...this.props.value,
            unit: ev.target.value,
        });
    }

    onIntervalChanged(ev) {
        this.props.onChange({
            ...this.defaultValue,
            ...this.props.value,
            interval: parseInt(ev.target.value, 10),
        });
    }
}
