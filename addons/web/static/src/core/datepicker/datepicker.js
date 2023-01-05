/** @odoo-module **/

import {
    areDateEquals,
    formatDate,
    formatDateTime,
    luxonToMoment,
    luxonToMomentFormat,
    parseDate,
    parseDateTime,
} from "@web/core/l10n/dates";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";
import { localization } from "@web/core/l10n/localization";
import { useAutofocus } from "@web/core/utils/hooks";
import { isIOS } from "@web/core/browser/feature_detection";

import {
    Component,
    onMounted,
    onWillUpdateProps,
    onWillUnmount,
    useExternalListener,
    useRef,
    useState,
} from "@odoo/owl";
const { DateTime } = luxon;

let datePickerId = 0;

/**
 * @param {string} format
 * @returns {boolean}
 */
function isValidStaticFormat(format) {
    return /^[\d\s/:-]+$/.test(DateTime.local().toFormat(format));
}

/**
 * @param {Function} fn
 * @returns {[any, null] | [null, Error]}
 */
function wrapError(fn) {
    return (...args) => {
        const result = [null, null];
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
        this.state = useState({ warning: false });

        this.datePickerId = `o_datepicker_${datePickerId++}`;
        // Manually keep track of the "open" state to write the date in the
        // static format just before bootstrap parses it.
        this.datePickerShown = false;

        this.initFormat();
        this.setDateAndFormat(this.props);

        useAutofocus();
        useExternalListener(window, "scroll", this.onWindowScroll, { capture: true });

        onMounted(this.onMounted);
        onWillUpdateProps(this.onWillUpdateProps);
        onWillUnmount(this.onWillUnmount);
    }

    onMounted() {
        this.bootstrapDateTimePicker(this.props);
        this.updateInput();

        window.$(this.rootRef.el).on("show.datetimepicker", () => {
            this.datePickerShown = true;
            this.inputRef.el.select();
        });
        window.$(this.rootRef.el).on("hide.datetimepicker", () => {
            this.datePickerShown = false;
            this.onDateChange({ useStatic: true });
        });
        window.$(this.rootRef.el).on("error.datetimepicker", () => false);
    }

    onWillUpdateProps(nextProps) {
        const pickerParams = {};
        for (const prop in nextProps) {
            if (!areDateEquals(this.props[prop], nextProps[prop])) {
                pickerParams[prop] = nextProps[prop];
            }
        }
        this.setDateAndFormat(nextProps);
        if ("date" in pickerParams || "format" in pickerParams) {
            this.updateInput();
        }
        this.bootstrapDateTimePicker(pickerParams);
    }

    onWillUnmount() {
        window.$(this.rootRef.el).off(); // Removes all jQuery events
        this.bootstrapDateTimePicker("destroy");
    }

    //---------------------------------------------------------------------
    // Protected
    //---------------------------------------------------------------------

    getOptions(useStatic = false) {
        return {
            format:
                !useStatic || isValidStaticFormat(this.format) ? this.format : this.staticFormat,
            locale: this.props.locale || (this.date && this.date.locale),
        };
    }

    /**
     * Initialises formatting and parsing parameters
     */
    initFormat() {
        this.defaultFormat = localization.dateFormat;
        this.staticFormat = "yyyy/MM/dd";
        this.formatValue = wrapError(formatDate);
        this.parseValue = wrapError(parseDate);
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
    }

    /**
     * Updates the input element with the current formatted date value.
     * @param {Object} [params={}]
     * @param {boolean} [params.useStatic]
     */
    updateInput({ useStatic } = {}) {
        const [formattedDate] = this.formatValue(this.date, this.getOptions(useStatic));
        if (formattedDate !== null) {
            this.inputRef.el.value = formattedDate;
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
            const params = {
                ...commandOrParams,
                date: this.date || null,
                format: luxonToMomentFormat(format),
                locale: commandOrParams.locale || (this.date && this.date.locale),
            };
            for (const prop in params) {
                if (params[prop] instanceof DateTime) {
                    params[prop] = params[prop].isValid ? luxonToMoment(params[prop]) : null;
                }
            }
            commandOrParams = params;
        }
        return window.$(this.rootRef.el).datetimepicker(commandOrParams);
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
     * datepicker is closed. The onDateTimeChanged prop is only called if the
     * date value has changed.
     * @param {Object} [params={}]
     * @param {boolean} [params.useStatic]
     */
    onDateChange({ useStatic } = {}) {
        const { value } = this.inputRef.el;
        const options = this.getOptions(useStatic);
        const parsedDate = this.parseValue(value, options)[0];
        this.state.warning = parsedDate && parsedDate > DateTime.local();
        if (value && !parsedDate) {
            // Reset to default (= given) date.
            this.updateInput();
        }
        if (parsedDate !== null && !areDateEquals(this.date, parsedDate)) {
            this.props.onDateTimeChanged(parsedDate);
        }
    }

    onInputKeydown(ev) {
        const hotkey = getActiveHotkey(ev);
        if (this.datePickerShown && hotkey === "escape") {
            this.bootstrapDateTimePicker("hide");
            this.inputRef.el.select();
            ev.preventDefault();
            ev.stopPropagation();
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
    inputId: "",
    maxDate: DateTime.fromObject({ year: 9999, month: 12, day: 31 }),
    minDate: DateTime.fromObject({ year: 1000 }),
    useCurrent: false,
    widgetParent: "body",
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
        this.formatValue = wrapError(formatDateTime);
        this.parseValue = wrapError(parseDateTime);
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
