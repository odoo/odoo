/** @odoo-module **/

import { PyDate, PyDateTime, PyRelativeDelta, PyTime, PyTimeDelta } from "./py_date";

export const BUILTINS = {
    /**
     * @param {any} value
     * @returns {boolean}
     */
    bool(value) {
        switch (typeof value) {
            case "number":
                return value !== 0;
            case "string":
                return value !== "";
            case "boolean":
                return value;
            case "object":
                if (value === null) {
                    return false;
                }
                if (value.isTrue) {
                    return value.isTrue();
                }
                return true;
        }
        return true;
    },

    time: {
        strftime(format) {
            return PyDateTime.now().strftime(format);
        },
    },

    context_today() {
        return PyDate.today();
    },

    get current_date() {
        // deprecated: today should be prefered
        return this.today;
    },

    get today() {
        return PyDate.today().strftime("%Y-%m-%d");
    },

    get now() {
        return PyDateTime.now().strftime("%Y-%m-%d %H:%M:%S");
    },

    datetime: {
        time: PyTime,
        timedelta: PyTimeDelta,
        datetime: PyDateTime,
        date: PyDate,
    },

    relativedelta: PyRelativeDelta,
};
