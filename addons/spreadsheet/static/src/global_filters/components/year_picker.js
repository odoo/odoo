/** @odoo-module */

import { DatePicker } from "@web/core/datepicker/datepicker";

const { DateTime } = luxon;

export class YearPicker extends DatePicker {
    /**
     * @override
     */
    initFormat() {
        super.initFormat();
        // moment.js format
        this.defaultFormat = "yyyy";
    }

    /**
     * @override
     */
    bootstrapDateTimePicker(commandOrParams, ...commandArgs) {
        if (typeof commandOrParams === "object") {
            const widgetParent = window.$(this.rootRef.el);
            commandOrParams = { ...commandOrParams, widgetParent };
        }
        super.bootstrapDateTimePicker(commandOrParams, ...commandArgs);
    }

    /**
     * @override
     */
    setDateAndFormat({ date, locale, format }) {
        super.setDateAndFormat({ date, locale, format });
        this.staticFormat = "yyyy";
    }
}

const props = {
    ...DatePicker.props,
    date: { type: DateTime, optional: true },
};
delete props["format"];

YearPicker.props = props;

YearPicker.defaultProps = {
    ...DatePicker.defaultProps,
};
