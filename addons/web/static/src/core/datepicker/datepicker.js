/** @odoo-module **/

import { localization } from "@web/core/l10n/localization";
import { registry } from "@web/core/registry";
import { useAutofocus } from "@web/core/utils/hooks";
import { isIOS } from "@web/core/browser/feature_detection";

const { Component, hooks } = owl;
const { DateTime } = luxon;
const { useExternalListener, useRef, useState } = hooks;

const formatters = registry.category("formatters");
const parsers = registry.category("parsers");

let datePickerId = 0;

/**
 * @param {DateTime} date
 * @returns {moment}
 */
const luxonDateToMomentDate = (date) => {
    return window.moment(String(date));
};

/**
 * @param {string} format
 * @returns {string}
 */
const luxonFormatToMomentFormat = (format) => {
    return format.replace(/[dy]/g, (x) => x.toUpperCase());
};

/**
 * @param {string} format
 * @returns {boolean}
 */
const isValidStaticFormat = (format) => {
    try {
        return /^[\d\s\/.,:-]+$/.test(DateTime.local().toFormat(format));
    } catch (_err) {
        return false;
    }
};

/**
 * Date picker
 *
 * This component exposes the API of the tempusdominus datepicker library.
 * As such, its template is a simple input that will open the TD datepicker
 * when clicked on. The component will also synchronize any user-input value
 * with the library widget and vice-versa.
 *
 * Note that all props given to this component will be passed as arguments to
 * instantiate the picker widget. Also any luxon date is automatically
 * stringified since tempusdominus only works with moment objects.
 * @extends Component
 */
export class DatePicker extends Component {
    setup() {
        this.inputRef = useRef("input");
        this.state = useState({ warning: false });

        this.datePickerId = `o_datepicker_${datePickerId++}`;
        // Manually keep track of the "open" state to write the date in the
        // static format just before bootstrap parses it.
        this.datePickerShown = false;

        this.initFormat();
        this.setDate(this.props);
        this.setFormat(this.props);

        useAutofocus();
        useExternalListener(window, "scroll", this.onWindowScroll);
    }

    mounted() {
        this.bootstrapDateTimePicker(this.props);
        this.updateInput();

        window.$(this.el).on("show.datetimepicker", () => {
            this.datePickerShown = true;
            this.inputRef.el.select();
        });
        window.$(this.el).on("hide.datetimepicker", () => {
            this.datePickerShown = false;
            this.onDateChange({ useStatic: true });
        });
        window.$(this.el).on("error.datetimepicker", () => false);
    }

    willUpdateProps(nextProps) {
        const pickerParams = {};
        let shouldUpdateInput = false;
        for (const prop in nextProps) {
            const prev = this.props[prop];
            const next = nextProps[prop];
            if ((prev instanceof DateTime && !prev.equals(next)) || prev !== next) {
                pickerParams[prop] = nextProps[prop];
                if (prop === "date") {
                    this.setDate(nextProps);
                    shouldUpdateInput = true;
                } else if (prop === "format") {
                    this.setFormat(nextProps);
                    shouldUpdateInput = true;
                }
            }
        }
        if (shouldUpdateInput) {
            this.updateInput();
        }
        this.bootstrapDateTimePicker(pickerParams);
    }

    willUnmount() {
        window.$(this.el).off(); // Removes all jQuery events

        this.bootstrapDateTimePicker("destroy");
    }

    //---------------------------------------------------------------------
    // Protected
    //---------------------------------------------------------------------

    getOptions(useStatic = false) {
        return {
            format: !useStatic || isValidStaticFormat(this.format) ? this.format : this.staticFormat,
            locale: this.date.locale,
            timezone: this.isLocal,
        };
    }

    /**
     * Initialises formatting and parsing parameters
     */
    initFormat() {
        this.defaultFormat = localization.dateFormat;
        this.staticFormat = "yyyy/MM/dd";
        this.formatValue = formatters.get("date");
        this.parseValue = parsers.get("date");
        this.isLocal = false;
    }

    /**
     * Sets the current date value. If a locale is provided, the given date
     * will first be set in that locale.
     * @param {Object} params
     * @param {DateTime} params.date
     * @param {string} [params.locale]
     */
    setDate({ date, locale }) {
        this.date = locale ? date.setLocale(locale) : date;
    }

    /**
     * Sets the current format.
     * @param {Object} params
     * @param {string} [params.format]
     */
    setFormat({ format }) {
        // Fallback to default localization format in `@web/core/l10n/dates.js`.
        this.format = format || this.defaultFormat;
    }

    /**
     * Updates the input element with the current formatted date value.
     * @param {Object} [params={}]
     * @param {boolean} [params.useStatic]
     */
    updateInput({ useStatic } = {}) {
        try {
            this.inputRef.el.value = this.formatValue(this.date, this.getOptions(useStatic));
        } catch (_err) {
            // Ignore
        }
    }

    //---------------------------------------------------------------------
    // Bootstrap datepicker
    //---------------------------------------------------------------------

    /**
     * Handles bootstrap datetimepicker calls.
     * @param {string | Object} commandOrParams
     */
    bootstrapDateTimePicker(commandOrParams) {
        if (typeof commandOrParams === "object") {
            const format = isValidStaticFormat(this.format) ? this.format : this.staticFormat;
            const params = { ...commandOrParams, format: luxonFormatToMomentFormat(format) };
            if (!params.locale && commandOrParams.date) {
                params.locale = commandOrParams.date.locale;
            }
            for (const prop in params) {
                if (params[prop] instanceof DateTime) {
                    const luxonDate = params[prop];
                    const momentDate = luxonDateToMomentDate(luxonDate);
                    params[prop] = momentDate;
                }
            }
            commandOrParams = params;
        }
        return window.$(this.el).datetimepicker(commandOrParams);
    }

    //---------------------------------------------------------------------
    // Handlers
    //---------------------------------------------------------------------

    onInputClick() {
        if (!this.datePickerShown) {
            this.updateInput({ useStatic: true });
        }
        this.bootstrapDateTimePicker("toggle");
    }

    /**
     * Called either when the input value has changed or when the boostrap
     * datepicker is closed. The actual "datetime-changed" emitted by the
     * component is only triggered if the date value has changed.
     * @param {Object} [params={}]
     * @param {boolean} [params.useStatic]
     */
    onDateChange({ useStatic } = {}) {
        let date;
        try {
            date = this.parseValue(this.inputRef.el.value, this.getOptions(useStatic));
        } catch (_err) {
            // Reset to default (= given) date.
        }
        if (!date || date.equals(this.date)) {
            this.updateInput();
        } else {
            this.state.warning = date > DateTime.local();
            this.trigger("datetime-changed", { date });
        }
    }

    /**
     * @param {Event} ev
     */
    onWindowScroll(ev) {
        if (!isIOS() && ev.target !== this.inputRef.el) {
            this.bootstrapDateTimePicker("hide");
        }
    }
}

DatePicker.defaultProps = {
    calendarWeeks: true,
    icons: {
        clear: "fa fa-delete",
        close: "fa fa-check primary",
        date: "fa fa-calendar",
        down: "fa fa-chevron-down",
        next: "fa fa-chevron-right",
        previous: "fa fa-chevron-left",
        time: "fa fa-clock-o",
        today: "fa fa-calendar-check-o",
        up: "fa fa-chevron-up",
    },
    maxDate: DateTime.fromObject({ year: 9999, month: 12, day: 31 }),
    minDate: DateTime.fromObject({ year: 1000 }),
    useCurrent: false,
    widgetParent: "body",
};
DatePicker.props = {
    // Components props
    date: DateTime,
    warn_future: { type: Boolean, optional: true },
    // Bootstrap datepicker options
    buttons: {
        type: Object,
        shape: {
            showClear: Boolean,
            showClose: Boolean,
            showToday: Boolean,
        },
        optional: true,
    },
    calendarWeeks: Boolean,
    format: { type: String, optional: true },
    icons: {
        type: Object,
        shape: {
            clear: String,
            close: String,
            date: String,
            down: String,
            next: String,
            previous: String,
            time: String,
            today: String,
            up: String,
        },
    },
    keyBinds: { validate: (kb) => typeof kb === "object" || kb === null, optional: true },
    locale: { type: String, optional: true },
    maxDate: DateTime,
    minDate: DateTime,
    readonly: { type: Boolean, optional: true },
    useCurrent: Boolean,
    widgetParent: String,
};
DatePicker.template = "web.DatePicker";

/**
 * Date/time picker
 *
 * Similar to the DatePicker component, adding the handling of more specific
 * time values: hour-minute-second.
 *
 * Once again, refer to the tempusdominus documentation for implementation
 * details.
 * @extends DatePicker
 */
export class DateTimePicker extends DatePicker {
    /**
     * @override
     */
    initFormat() {
        this.defaultFormat = localization.dateTimeFormat;
        this.staticFormat = "yyyy/MM/dd HH:mm:ss";
        this.formatValue = formatters.get("datetime");
        this.parseValue = parsers.get("datetime");
        this.isLocal = true;
    }
}

DateTimePicker.defaultProps = {
    ...DatePicker.defaultProps,
    buttons: {
        showClear: false,
        showClose: true,
        showToday: false,
    },
};
