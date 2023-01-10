odoo.define('web.DatePickerOwl', function (require) {
    "use strict";

    const field_utils = require('web.field_utils');
    const time = require('web.time');
    const { useAutofocus } = require('web.custom_hooks');

    const { Component, hooks } = owl;
    const { useExternalListener, useRef, useState } = hooks;

    let datePickerId = 0;

    /**
     * Date picker
     *
     * This component exposes the API of the tempusdominus datepicker library.
     * As such, its template is a simple input that will open the TD datepicker
     * when clicked on. The component will also synchronize any user-input value
     * with the library widget and vice-vera.
     *
     * For further details regarding the implementation of the picker itself, please
     * refer to the official tempusdominus documentation (note: all props given
     * to this component will be passed as arguments to instantiate the picker widget).
     * @extends Component
     */
    class DatePicker extends Component {
        constructor() {
            super(...arguments);

            this.inputRef = useRef('input');
            this.state = useState({ warning: false });

            this.datePickerId = `o_datepicker_${datePickerId++}`;
            this.typeOfDate = 'date';

            useAutofocus();
            useExternalListener(window, 'scroll', this._onWindowScroll);
        }

        mounted() {
            $(this.el).on('show.datetimepicker', this._onDateTimePickerShow.bind(this));
            $(this.el).on('hide.datetimepicker', this._onDateTimePickerHide.bind(this));
            $(this.el).on('error.datetimepicker', () => false);

            const pickerOptions = Object.assign({ format: this.defaultFormat }, this.props);
            this._datetimepicker(pickerOptions);
            this.inputRef.el.value = this._formatDate(this.props.date);
        }

        willUnmount() {
            this._datetimepicker('destroy');
        }

        willUpdateProps(nextProps) {
            for (const prop in nextProps) {
                this._datetimepicker(prop, nextProps[prop]);
            }
            if (nextProps.date) {
                this.inputRef.el.value = this._formatDate(nextProps.date);
            }
        }

        //---------------------------------------------------------------------
        // Private
        //---------------------------------------------------------------------

        /**
         * @returns {string}
         */
        get defaultFormat() {
            return time.getLangDateFormat();
        }

        //---------------------------------------------------------------------
        // Private
        //---------------------------------------------------------------------

        /**
         * Handle bootstrap datetimepicker calls.
         * @private
         * @param {...any} args anything that will be passed to the datetimepicker function.
         */
        _datetimepicker(...args) {
            this.ignoreBootstrapEvents = true;
            $(this.el).datetimepicker(...args);
            this.ignoreBootstrapEvents = false;
        }

        /**
         * @private
         * @param {moment} date
         * @returns {string}
         */
        _formatDate(date) {
            try {
                return field_utils.format[this.typeOfDate](date, null, { timezone: false });
            } catch (err) {
                return false;
            }
        }

        /**
         * @private
         * @param {string|false} value
         * @returns {moment}
         */
        _parseInput(inputValue) {
            try {
                return field_utils.parse[this.typeOfDate](inputValue, null, { timezone: false });
            } catch (err) {
                return false;
            }
        }

        //---------------------------------------------------------------------
        // Handlers
        //---------------------------------------------------------------------

        /**
         * Reacts to the datetimepicker being hidden
         * Used to unbind the scroll event from the datetimepicker
         * @private
         */
        _onDateTimePickerHide() {
            if (this.ignoreBootstrapEvents) {
                return;
            }
            const date = this._parseInput(this.inputRef.el.value);
            this.state.warning = date.format('YYYY-MM-DD') > moment().format('YYYY-MM-DD');
            this.trigger('datetime-changed', { date });
        }

        /**
         * Reacts to the datetimepicker being shown
         * Could set/verify our widget value
         * And subsequently update the datetimepicker
         * @private
         */
        _onDateTimePickerShow() {
            if (this.ignoreBootstrapEvents) {
                return;
            }
            this.inputRef.el.select();
        }

        /**
         * @private
         */
        _onInputClick() {
            this._datetimepicker('toggle');
        }

        /**
         * @private
         */
        _onInputChange() {
            const date = this._parseInput(this.inputRef.el.value);
            if (date) {
                this.state.warning = date.format('YYYY-MM-DD') > moment().format('YYYY-MM-DD');
                this.trigger('datetime-changed', { date });
            } else {
                this.inputRef.el.value = this._formatDate(this.props.date);
            }
        }

        /**
         * @private
         */
        _onWindowScroll(ev) {
            if (ev.target !== this.inputRef.el) {
                this._datetimepicker('hide');
            }
        }
    }

    DatePicker.defaultProps = {
        calendarWeeks: true,
        icons: {
            clear: 'fa fa-delete',
            close: 'fa fa-check primary',
            date: 'fa fa-calendar',
            down: 'fa fa-chevron-down',
            next: 'fa fa-chevron-right',
            previous: 'fa fa-chevron-left',
            time: 'fa fa-clock-o',
            today: 'fa fa-calendar-check-o',
            up: 'fa fa-chevron-up',
        },
        get locale() {return moment.locale();},
        maxDate: moment({ y: 9999, M: 11, d: 31 }),
        minDate: moment({ y: 1000 }),
        useCurrent: false,
        widgetParent: 'body',
    };
    DatePicker.props = {
        // Actual date value
        date: moment,
        // Other props
        buttons: {
            type: Object,
            shape: {
                showClear: Boolean,
                showClose: Boolean,
                showToday: Boolean,
            },
            optional: 1,
        },
        calendarWeeks: Boolean,
        format: { type: String, optional: 1 },
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
        keyBinds: { validate: kb => typeof kb === 'object' || kb === null, optional: 1 },
        locale: String,
        maxDate: moment,
        minDate: moment,
        readonly: { type: Boolean, optional: 1 },
        useCurrent: Boolean,
        widgetParent: String,
    };
    DatePicker.template = "web.Legacy.DatePicker";

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
    class DateTimePicker extends DatePicker {
        constructor() {
            super(...arguments);

            this.typeOfDate = 'datetime';
        }

        /**
         * @override
         */
        get defaultFormat() {
            return time.getLangDatetimeFormat();
        }
    }

    DateTimePicker.defaultProps = Object.assign(Object.create(DatePicker.defaultProps), {
        buttons: {
            showClear: false,
            showClose: true,
            showToday: false,
        },
    });

    return {
        DatePicker,
        DateTimePicker,
    };
});
