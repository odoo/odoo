/** @odoo-module **/

import {
    Component,
    onMounted,
    onWillUnmount,
    onWillUpdateProps,
    useExternalListener,
    useRef,
    useState,
} from "@odoo/owl";
import { isMobileOS } from "@web/core/browser/feature_detection";
import {
    formatDate,
    formatDateTime,
    luxonToMoment,
    luxonToMomentFormat,
    momentToLuxon,
    parseDate,
    parseDateTime,
} from "@web/core/l10n/dates";
import { localization } from "@web/core/l10n/localization";
import { useAutofocus } from "@web/core/utils/hooks";
import { pick } from "../utils/objects";

const { DateTime } = luxon;

let datePickerId = 0;

/**
 * @param {unknown} value1
 * @param {unknown} value2
 */
function areEqual(value1, value2) {
    if (value1 && value2) {
        // Only compare date values
        return Number(value1) === Number(value2);
    } else {
        return value1 === value2;
    }
}

/**
 * @template {(...args: any[]) => any} F
 * @template T
 * @param {F} fn
 * @param {T} defaultValue
 * @returns {[any, null] | [null, Error]}
 */
function wrapError(fn, defaultValue) {
    return (...args) => {
        const result = [defaultValue, null];
        try {
            result[0] = fn(...args);
        } catch (_err) {
            result[1] = _err;
        }
        return result;
    };
}

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
        this.rootRef = useRef("root");
        this.inputRef = useRef("input");
        this.hiddenInputRef = useRef("hiddenInput");
        this.state = useState({ warning: false });

        // Picker variables
        this.datePickerId = `o_datepicker_${datePickerId++}`;
        /**
         * Manually keep track of the "open" state to write the date in the
         * static format just before bootstrap parses it.
         */
        this.isPickerOpen = false;
        /** @type {DateTime | null} */
        this.pickerDate = null;
        this.ignorePickerEvents = true;

        this.initFormat();
        this.setDateAndFormat(this.props);

        useAutofocus();
        useExternalListener(window, "click", this.onWindowClick, { capture: true });
        useExternalListener(window, "scroll", this.onWindowScroll, { capture: true });

        onMounted(this.onMounted);
        onWillUpdateProps(this.onWillUpdateProps);
        onWillUnmount(this.onWillUnmount);
    }

    onMounted() {
        this.bootstrapDateTimePicker(this.props);
        this.updateInput(this.date);

        this.addPickerListener("show", () => {
            this.isPickerOpen = true;
            this.inputRef.el.select();
        });
        this.addPickerListener("change", ({ date }) => {
            if (date && this.isPickerOpen) {
                const { locale } = this.getOptions();
                this.pickerDate = momentToLuxon(date).setLocale(locale);
                this.updateInput(this.pickerDate);
            }
        });
        this.addPickerListener("hide", () => {
            this.isPickerOpen = false;
            this.onDateChange();
            this.pickerDate = null;
        });
        this.addPickerListener("error", () => false);

        this.ignorePickerEvents = false;
    }

    onWillUpdateProps(nextProps) {
        this.ignorePickerEvents = true;
        this.setDateAndFormat(nextProps);
        const shouldUpdate = Object.entries(pick(nextProps, "date", "format")).some(
            ([key, val]) => !areEqual(this.props[key], val)
        );
        if (shouldUpdate) {
            this.updateInput(this.date);
        }
        if (this.isPickerOpen) {
            this.bootstrapDateTimePicker("hide");
            this.bootstrapDateTimePicker("show");
        }
        this.ignorePickerEvents = false;
    }

    onWillUnmount() {
        window.$(this.rootRef.el).off(); // Removes all jQuery events
        this.bootstrapDateTimePicker("destroy");
    }

    //---------------------------------------------------------------------
    // Protected
    //---------------------------------------------------------------------

    /**
     *
     * @param {string} type
     * @param {(ev: JQuery.Event) => any} listener
     */
    addPickerListener(type, listener) {
        return window.$(this.rootRef.el).on(`${type}.datetimepicker`, (ev) => {
            if (this.ignorePickerEvents) {
                return false;
            }
            return listener(ev);
        });
    }

    getOptions() {
        return {
            format: this.format,
            locale: this.props.locale || (this.date && this.date.locale),
        };
    }

    /**
     * Initialises formatting and parsing parameters
     */
    initFormat() {
        this.defaultFormat = localization.dateFormat;
        this.formatValue = wrapError(formatDate, "");
        this.parseValue = wrapError(parseDate, false);
        this.isLocal = false;
    }

    /**
     * Sets the current date value. If a locale is provided, the given date
     * will first be set in that locale.
     * @param {Object} params
     * @param {DateTime} params.date
     * @param {string} [params.locale]
     * @param {string} [params.format]
     */
    setDateAndFormat({ date, locale, format }) {
        this.date = date && locale ? date.setLocale(locale) : date;
        // Fallback to default localization format in `@web/core/l10n/dates.js`.
        this.format = format || this.defaultFormat;
        this.staticFormat = "yyyy-MM-dd";
    }

    /**
     * Updates the input element with the current formatted date value.
     *
     * @param {DateTime} value
     */
    updateInput(value) {
        value = value || false;
        const options = this.getOptions();
        const [formattedValue, error] = this.formatValue(value, options);
        if (!error) {
            this.inputRef.el.value = formattedValue;
            [this.hiddenInputRef.el.value] = this.formatValue(value, {
                ...options,
                format: this.staticFormat,
            });
            this.props.onUpdateInput(formattedValue);
        }
        return formattedValue;
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
            const params = {
                ...commandOrParams,
                date: this.date || null,
                format: luxonToMomentFormat(this.staticFormat),
                locale: commandOrParams.locale || (this.date && this.date.locale),
            };
            for (const prop in params) {
                if (params[prop] instanceof DateTime) {
                    params[prop] = luxonToMoment(params[prop]);
                }
            }
            commandOrParams = params;
        }

        window.$(this.rootRef.el).datetimepicker(commandOrParams);
    }

    //---------------------------------------------------------------------
    // Handlers
    //---------------------------------------------------------------------

    /**
     * Called either when the input value has changed or when the boostrap
     * datepicker is closed. The onDateTimeChanged prop is only called if the
     * date value has changed.
     */
    onDateChange() {
        const [value, error] = this.pickerDate
            ? [this.pickerDate, null]
            : this.parseValue(this.inputRef.el.value, this.getOptions());

        this.state.warning = value && value > DateTime.local();

        if (error || areEqual(this.date, value)) {
            // Force current value
            this.updateInput(this.date);
        } else {
            this.props.onDateTimeChanged(value);
        }

        if (this.pickerDate) {
            this.inputRef.el.select();
        }
    }

    onInputChange() {
        this.onDateChange();
    }

    /**
     * @param {InputEvent} ev
     */
    onInputInput(ev) {
        this.pickerDate = null;
        return this.props.onInput(ev);
    }

    /**
     * @param {KeyboardEvent} ev
     */
    onInputKeydown(ev) {
        switch (ev.key) {
            case "Escape": {
                if (this.isPickerOpen) {
                    ev.preventDefault();
                    ev.stopPropagation();
                    this.bootstrapDateTimePicker("hide");
                    this.inputRef.el.select();
                }
                break;
            }
            case "Tab": {
                this.bootstrapDateTimePicker("hide");
                break;
            }
        }
    }

    /**
     * @param {PointerEvent} ev
     */
    onWindowClick({ target }) {
        if (target.closest(".bootstrap-datetimepicker-widget")) {
            return;
        } else if (this.rootRef.el.contains(target)) {
            this.bootstrapDateTimePicker("toggle");
        } else {
            this.bootstrapDateTimePicker("hide");
        }
    }

    /**
     * @param {Event} ev
     */
    onWindowScroll(ev) {
        if (!isMobileOS() && ev.target !== this.inputRef.el) {
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
    inputId: "",
    maxDate: DateTime.fromObject({ year: 9999, month: 12, day: 31 }),
    minDate: DateTime.fromObject({ year: 1000 }),
    useCurrent: false,
    widgetParent: "body",
    onInput: () => {},
    onUpdateInput: () => {},
};
DatePicker.props = {
    // Components props
    onDateTimeChanged: Function,
    date: { type: [DateTime, { value: false }], optional: true },
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
    calendarWeeks: { type: Boolean, optional: true },
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
        optional: true,
    },
    inputId: { type: String, optional: true },
    keyBinds: { validate: (kb) => typeof kb === "object" || kb === null, optional: true },
    locale: { type: String, optional: true },
    maxDate: { type: DateTime, optional: true },
    minDate: { type: DateTime, optional: true },
    readonly: { type: Boolean, optional: true },
    useCurrent: { type: Boolean, optional: true },
    widgetParent: { type: String, optional: true },
    daysOfWeekDisabled: { type: Array, optional: true },
    placeholder: { type: String, optional: true },
    onInput: { type: Function, optional: true },
    onUpdateInput: { type: Function, optional: true },
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
        this.formatValue = wrapError(formatDateTime, "");
        this.parseValue = wrapError(parseDateTime, false);
        this.isLocal = true;
    }

    /**
     * @override
     */
    setDateAndFormat(nextProps) {
        super.setDateAndFormat(nextProps);

        this.staticFormat += ` ${/h/.test(this.format) ? "hh" : "HH"}:mm:ss`;
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
