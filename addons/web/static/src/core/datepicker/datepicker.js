/** @odoo-module **/

import { localization } from "@web/core/l10n/localization";
import { registry } from "@web/core/registry";
import { useAutofocus } from "@web/core/utils/hooks";

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

        this.initFormat();
        this.setDate(this.props);

        useAutofocus();
        useExternalListener(window, "scroll", this.onWindowScroll);
    }

    mounted() {
        window.$(this.el).on("show.datetimepicker", () => this.inputRef.el.select());
        window.$(this.el).on("hide.datetimepicker", () => this.onDateChange());
        window.$(this.el).on("error.datetimepicker", () => false); // Ignores datepicker errors

        this.bootstrapDateTimePicker(this.props);
        this.updateInput();
    }

    willUpdateProps(nextProps) {
        const pickerParams = {};
        for (const prop in nextProps) {
            if (this.props[prop] !== nextProps[prop]) {
                pickerParams[prop] = nextProps[prop];
                if (prop === "date") {
                    this.setDate(nextProps);
                    this.updateInput();
                }
            }
        }
        this.bootstrapDateTimePicker(pickerParams);
    }

    willUnmount() {
        window.$(this.el).off(); // Removes all jQuery events

        this.bootstrapDateTimePicker("destroy");
    }

    //---------------------------------------------------------------------
    // Getters
    //---------------------------------------------------------------------

    get options() {
        return {
            // Fallback to default localization format in `core/l10n/dates.js`.
            format: this.props.format,
            locale: this.props.locale || this.date.locale,
            timezone: this.isLocal,
        };
    }

    //---------------------------------------------------------------------
    // Protected
    //---------------------------------------------------------------------

    /**
     * Initialises formatting and parsing parameters
     */
    initFormat() {
        this.defaultFormat = localization.dateFormat;
        this.format = formatters.get("date");
        this.parse = parsers.get("date");
        this.isLocal = false;
    }

    /**
     * Sets the current date value. If a locale is provided, the given date
     * will first be set in that locale.
     * @param {object} params
     * @param {DateTime} params.date
     * @param {string} [params.locale]
     */
    setDate({ date, locale }) {
        this.date = locale ? date.setLocale(locale) : date;
    }

    /**
     * Updates the input element with the current formatted date value.
     */
    updateInput() {
        try {
            this.inputRef.el.value = this.format(this.date, this.options);
        } catch (err) {
            // Do nothing
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
            const format = luxonFormatToMomentFormat(this.props.format || this.defaultFormat);
            const params = { ...commandOrParams, format };
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
        window.$(this.el).datetimepicker(commandOrParams);
    }

    //---------------------------------------------------------------------
    // Handlers
    //---------------------------------------------------------------------

    onInputClick() {
        this.bootstrapDateTimePicker("toggle");
    }

    /**
     * Called either when the input value has changed or when the boostrap
     * datepicker is closed. The actual "datetime-changed" emitted by the
     * component is only triggered if the date value has changed.
     */
    onDateChange() {
        try {
            const date = this.parse(this.inputRef.el.value, this.options);
            if (!date.equals(this.props.date)) {
                this.state.warning = date > DateTime.local();
                this.trigger("datetime-changed", { date });
            }
        } catch (err) {
            // Reset to default (= given) date.
            this.updateInput();
        }
    }

    /**
     * @param {Event} ev
     */
    onWindowScroll(ev) {
        if (ev.target !== this.inputRef.el) {
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
        this.format = formatters.get("datetime");
        this.parse = parsers.get("datetime");
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
