odoo.define('website.s_website_form', function (require) {
    'use strict';

    var core = require('web.core');
    var time = require('web.time');
    const {ReCaptcha} = require('google_recaptcha.ReCaptchaV3');
    const session = require('web.session');
    var ajax = require('web.ajax');
    var publicWidget = require('web.public.widget');
    const dom = require('web.dom');
    const concurrency = require('web.concurrency');

    var _t = core._t;
    var qweb = core.qweb;

    publicWidget.registry.EditModeWebsiteForm = publicWidget.Widget.extend({
        selector: '.s_website_form form, form.s_website_form', // !compatibility
        disabledInEditableMode: false,
        /**
         * @override
         */
        start: function () {
            if (this.editableMode) {
                // We do not initialize the datetime picker in edit mode but want the dates to be formated
                const dateTimeFormat = time.getLangDatetimeFormat();
                const dateFormat = time.getLangDateFormat();
                this.$target[0].querySelectorAll('.s_website_form_input.datetimepicker-input').forEach(el => {
                    const value = el.getAttribute('value');
                    if (value) {
                        const format = el.closest('.s_website_form_field').dataset.type === 'date' ? dateFormat : dateTimeFormat;
                        el.value = moment.unix(value).format(format);
                    }
                });
            }
            return this._super(...arguments);
        },
    });

    publicWidget.registry.s_website_form = publicWidget.Widget.extend({
        selector: '.s_website_form form, form.s_website_form', // !compatibility
        xmlDependencies: ['/website/static/src/xml/website_form.xml'],
        events: {
            'click .s_website_form_send, .o_website_form_send': 'send', // !compatibility
        },

        /**
         * @constructor
         */
        init: function () {
            this._super(...arguments);
            this._recaptcha = new ReCaptcha();
            this.initialValues = new Map();
            this._visibilityFunctionByFieldName = new Map();
            this._visibilityFunctionByFieldEl = new Map();
            this.__started = new Promise(resolve => this.__startResolve = resolve);
        },
        willStart: async function () {
            const res = this._super(...arguments);
            if (!this.$target[0].classList.contains('s_website_form_no_recaptcha')) {
                this._recaptchaLoaded = true;
                this._recaptcha.loadLibs();
            }
            // fetch user data (required by fill-with behavior)
            this.preFillValues = {};
            if (session.user_id) {
                this.preFillValues = (await this._rpc({
                    model: 'res.users',
                    method: 'read',
                    args: [session.user_id, this._getUserPreFillFields()],
                }))[0] || {};
            }

            return res;
        },
        start: function () {
            // Prepare visibility data and update field visibilities
            const visibilityFunctionsByFieldName = new Map();
            for (const fieldEl of this.$target[0].querySelectorAll('[data-visibility-dependency]')) {
                const inputName = fieldEl.querySelector('.s_website_form_input').name;
                if (!visibilityFunctionsByFieldName.has(inputName)) {
                    visibilityFunctionsByFieldName.set(inputName, []);
                }
                const func = this._buildVisibilityFunction(fieldEl);
                visibilityFunctionsByFieldName.get(inputName).push(func);
                this._visibilityFunctionByFieldEl.set(fieldEl, func);
            }
            for (const [name, funcs] of visibilityFunctionsByFieldName.entries()) {
                this._visibilityFunctionByFieldName.set(name, () => funcs.some(func => func()));
            }
            this._updateFieldsVisibility();

            this._onFieldInputDebounced = _.debounce(this._onFieldInput.bind(this), 400);
            this.$el.on('input.s_website_form', '.s_website_form_field', this._onFieldInputDebounced);

            // Initialize datetimepickers
            var datepickers_options = {
                minDate: moment({y: 1000}),
                maxDate: moment({y: 9999, M: 11, d: 31}),
                calendarWeeks: true,
                icons: {
                    time: 'fa fa-clock-o',
                    date: 'fa fa-calendar',
                    next: 'fa fa-chevron-right',
                    previous: 'fa fa-chevron-left',
                    up: 'fa fa-chevron-up',
                    down: 'fa fa-chevron-down',
                },
                locale: moment.locale(),
                format: time.getLangDatetimeFormat(),
                extraFormats: ['X'],
            };
            const $datetimes = this.$target.find('.s_website_form_datetime, .o_website_form_datetime'); // !compatibility
            $datetimes.datetimepicker(datepickers_options);

            // Adapt options to date-only pickers
            datepickers_options.format = time.getLangDateFormat();
            const $dates = this.$target.find('.s_website_form_date, .o_website_form_date'); // !compatibility
            $dates.datetimepicker(datepickers_options);

            this.$allDates = $datetimes.add($dates);
            this.$allDates.addClass('s_website_form_datepicker_initialized');

            // Display form values from tag having data-for attribute
            // It's necessary to handle field values generated on server-side
            // Because, using t-att- inside form make it non-editable
            // Data-fill-with attribute is given during registry and is used by
            // to know which user data should be used to prfill fields.
            const dataForEl = document.querySelector(`[data-for='${this.$target[0].id}']`);
            if (dataForEl || Object.keys(this.preFillValues).length) {
                const dataForValues = dataForEl ?
                    JSON.parse(dataForEl.dataset.values
                        .replace('False', '""')
                        .replace('None', '""')
                        .replace(/'/g, '"')
                    ) : {};
                const fieldNames = this.$target.serializeArray().map(el => el.name);
                // All types of inputs do not have a value property (eg:hidden),
                // for these inputs any function that is supposed to put a value
                // property actually puts a HTML value attribute. Because of
                // this, we have to clean up these values at destroy or else the
                // data loaded here could become default values. We could set
                // the values to submit() for these fields but this could break
                // customizations that use the current behavior as a feature.
                for (const name of fieldNames) {
                    const fieldEl = this.$target[0].querySelector(`[name="${name}"]`);

                    // In general, we want the data-for and prefill values to
                    // take priority over set default values. The 'email_to'
                    // field is however treated as an exception at the moment
                    // so that values set by users are always used.
                    if (name === 'email_to' && fieldEl.value
                            // The following value is the default value that
                            // is set if the form is edited in any way. (see the
                            // website.form_editor_registry module in editor
                            // assets bundle).
                            // TODO that value should probably never be forced
                            // unless explicitely manipulated by the user or on
                            // custom form addition but that seems risky to
                            // change as a stable fix.
                            && fieldEl.value !== 'info@yourcompany.example.com') {
                        continue;
                    }

                    let newValue;
                    if (dataForValues && dataForValues[name]) {
                        newValue = dataForValues[name];
                    } else if (this.preFillValues[fieldEl.dataset.fillWith]) {
                        newValue = this.preFillValues[fieldEl.dataset.fillWith];
                    }
                    if (newValue) {
                        this.initialValues.set(fieldEl, fieldEl.getAttribute('value'));
                        fieldEl.value = newValue;
                    }
                }
            }

            // Check disabled states
            this.inputEls = this.$target[0].querySelectorAll('.s_website_form_field.s_website_form_field_hidden_if .s_website_form_input');
            this._disabledStates = new Map();
            for (const inputEl of this.inputEls) {
                this._disabledStates[inputEl] = inputEl.disabled;
            }

            return this._super(...arguments).then(() => this.__startResolve());
        },

        destroy: function () {
            this._super.apply(this, arguments);
            this.$target.find('button').off('click');

            // Empty imputs
            this.$target[0].reset();

            // Apply default values
            const dateTimeFormat = time.getLangDatetimeFormat();
            const dateFormat = time.getLangDateFormat();
            this.$target[0].querySelectorAll('input[type="text"], input[type="email"], input[type="number"]').forEach(el => {
                let value = el.getAttribute('value');
                if (value) {
                    if (el.classList.contains('datetimepicker-input')) {
                        const format = el.closest('.s_website_form_field').dataset.type === 'date' ? dateFormat : dateTimeFormat;
                        value = moment.unix(value).format(format);
                    }
                    el.value = value;
                }
            });
            this.$target[0].querySelectorAll('textarea').forEach(el => el.value = el.textContent);

            // Remove saving of the error colors
            this.$target.find('.o_has_error').removeClass('o_has_error').find('.form-control, .custom-select').removeClass('is-invalid');

            // Remove the status message
            this.$target.find('#s_website_form_result, #o_website_form_result').empty(); // !compatibility

            // Remove the success message and display the form
            this.$target.removeClass('d-none');
            this.$target.parent().find('.s_website_form_end_message').addClass('d-none');

            // Reinitialize dates
            this.$allDates.removeClass('s_website_form_datepicker_initialized');

            // Restore disabled attribute
            for (const inputEl of this.inputEls) {
                inputEl.disabled = !!this._disabledStates.get(inputEl);
            }

            // All 'hidden if' fields start with d-none
            this.$target[0].querySelectorAll('.s_website_form_field_hidden_if:not(.d-none)').forEach(el => el.classList.add('d-none'));

            // Reset the initial default values.
            for (const [fieldEl, initialValue] of this.initialValues.entries()) {
                if (initialValue) {
                    fieldEl.setAttribute('value', initialValue);
                } else {
                    fieldEl.removeAttribute('value');
                }
            }

            this.$el.off('.s_website_form');
        },

        send: async function (e) {
            e.preventDefault(); // Prevent the default submit behavior
             // Prevent users from crazy clicking
            const $button = this.$target.find('.s_website_form_send, .o_website_form_send');
            $button.addClass('disabled') // !compatibility
                   .attr('disabled', 'disabled');
            this.restoreBtnLoading = dom.addButtonLoadingEffect($button[0]);

            var self = this;

            self.$target.find('#s_website_form_result, #o_website_form_result').empty(); // !compatibility
            if (!self.check_error_fields({})) {
                self.update_status('error', _t("Please fill in the form correctly."));
                return false;
            }

            // Prepare form inputs
            this.form_fields = this.$target.serializeArray();
            $.each(this.$target.find('input[type=file]:not([disabled])'), (outer_index, input) => {
                $.each($(input).prop('files'), function (index, file) {
                    // Index field name as ajax won't accept arrays of files
                    // when aggregating multiple files into a single field value
                    self.form_fields.push({
                        name: input.name + '[' + outer_index + '][' + index + ']',
                        value: file
                    });
                });
            });

            // Serialize form inputs into a single object
            // Aggregate multiple values into arrays
            var form_values = {};
            _.each(this.form_fields, function (input) {
                if (input.name in form_values) {
                    // If a value already exists for this field,
                    // we are facing a x2many field, so we store
                    // the values in an array.
                    if (Array.isArray(form_values[input.name])) {
                        form_values[input.name].push(input.value);
                    } else {
                        form_values[input.name] = [form_values[input.name], input.value];
                    }
                } else {
                    if (input.value !== '') {
                        form_values[input.name] = input.value;
                    }
                }
            });

            // force server date format usage for existing fields
            this.$target.find('.s_website_form_field:not(.s_website_form_custom)')
            .find('.s_website_form_date, .s_website_form_datetime').each(function () {
                var date = $(this).datetimepicker('viewDate').clone().locale('en');
                var format = 'YYYY-MM-DD';
                if ($(this).hasClass('s_website_form_datetime')) {
                    date = date.utc();
                    format = 'YYYY-MM-DD HH:mm:ss';
                }
                form_values[$(this).find('input').attr('name')] = date.format(format);
            });

            if (this._recaptchaLoaded) {
                const tokenObj = await this._recaptcha.getToken('website_form');
                if (tokenObj.token) {
                    form_values['recaptcha_token_response'] = tokenObj.token;
                } else if (tokenObj.error) {
                    self.update_status('error', tokenObj.error);
                    return false;
                }
            }

            // Post form and handle result
            ajax.post(this.$target.attr('action') + (this.$target.data('force_action') || this.$target.data('model_name')), form_values)
            .then(async function (result_data) {
                // Restore send button behavior
                self.$target.find('.s_website_form_send, .o_website_form_send')
                    .removeAttr('disabled')
                    .removeClass('disabled'); // !compatibility
                result_data = JSON.parse(result_data);
                if (!result_data.id) {
                    // Failure, the server didn't return the created record ID
                    self.update_status('error', result_data.error ? result_data.error : false);
                    if (result_data.error_fields) {
                        // If the server return a list of bad fields, show these fields for users
                        self.check_error_fields(result_data.error_fields);
                    }
                } else {
                    // Success, redirect or update status
                    let successMode = self.$target[0].dataset.successMode;
                    let successPage = self.$target[0].dataset.successPage;
                    if (!successMode) {
                        successPage = self.$target.attr('data-success_page'); // Compatibility
                        successMode = successPage ? 'redirect' : 'nothing';
                    }
                    switch (successMode) {
                        case 'redirect': {
                            successPage = successPage.startsWith("/#") ? successPage.slice(1) : successPage;
                            if (successPage.charAt(0) === "#") {
                                await dom.scrollTo($(successPage)[0], {
                                    duration: 500,
                                    extraOffset: 0,
                                });
                                break;
                            }
                            $(window.location).attr('href', successPage);
                            return;
                        }
                        case 'message': {
                            // Prevent double-clicking on the send button and
                            // add a upload loading effect (delay before success
                            // message)
                            await concurrency.delay(dom.DEBOUNCE);

                            self.$target[0].classList.add('d-none');
                            self.$target[0].parentElement.querySelector('.s_website_form_end_message').classList.remove('d-none');
                            return;
                        }
                        default: {
                            // Prevent double-clicking on the send button and
                            // add a upload loading effect (delay before success
                            // message)
                            await concurrency.delay(dom.DEBOUNCE);

                            self.update_status('success');
                            break;
                        }
                    }

                    self.$target[0].reset();
                    self.restoreBtnLoading();
                }
            })
            .guardedCatch(error => {
                this.update_status(
                    'error',
                    error.status && error.status === 413 ? _t("Uploaded file is too large.") : "",
                );
            });
        },

        check_error_fields: function (error_fields) {
            var self = this;
            var form_valid = true;
            // Loop on all fields
            this.$target.find('.form-field, .s_website_form_field').each(function (k, field) { // !compatibility
                var $field = $(field);
                // FIXME that seems broken, "for" does not contain the field
                // but this is used to retrieve errors sent from the server...
                // need more investigation.
                var field_name = $field.find('.col-form-label').attr('for');

                // Validate inputs for this field
                var inputs = $field.find('.s_website_form_input, .o_website_form_input').not('#editable_select'); // !compatibility
                var invalid_inputs = inputs.toArray().filter(function (input, k, inputs) {
                    // Special check for multiple required checkbox for same
                    // field as it seems checkValidity forces every required
                    // checkbox to be checked, instead of looking at other
                    // checkboxes with the same name and only requiring one
                    // of them to be valid.
                    if (input.required && input.type === 'checkbox') {
                        // Considering we are currently processing a single
                        // field, we can assume that all checkboxes in the
                        // inputs variable have the same name
                        // TODO should be improved: probably do not need to
                        // filter neither on required, nor on checkbox and
                        // checking the validity of the group of checkbox is
                        // currently done for each checkbox of that group...
                        var checkboxes = _.filter(inputs, function (input) {
                            return input.required && input.type === 'checkbox';
                        });
                        return !_.any(checkboxes, checkbox => checkbox.checkValidity());

                    // Special cases for dates and datetimes
                    // FIXME this seems like dead code, the inputs do not use
                    // those classes, their parent does (but it seemed to work
                    // at some point given that https://github.com/odoo/odoo/commit/75e03c0f7692a112e1b0fa33267f4939363f3871
                    // was made)... need more investigation (if restored,
                    // consider checking the date inputs are not disabled before
                    // saying they are invalid (see checkValidity used here))
                    } else if ($(input).hasClass('s_website_form_date') || $(input).hasClass('o_website_form_date')) { // !compatibility
                        if (!self.is_datetime_valid(input.value, 'date')) {
                            return true;
                        }
                    } else if ($(input).hasClass('s_website_form_datetime') || $(input).hasClass('o_website_form_datetime')) { // !compatibility
                        if (!self.is_datetime_valid(input.value, 'datetime')) {
                            return true;
                        }
                    }

                    // Note that checkValidity also takes care of the case where
                    // the input is disabled, in which case, it is considered
                    // valid (as the data will not be sent anyway).
                    // This takes care of conditionally-hidden fields (whose
                    // inputs are disabled while they are hidden) which should
                    // not require validation while they are hidden. Indeed,
                    // their purpose is to be able to enter additional data when
                    // some condition is fulfilled. If such a field is required,
                    // it is only required when visible for example.
                    return !input.checkValidity();
                });

                // Update field color if invalid or erroneous
                const $controls = $field.find('.form-control, .custom-select, .form-check-input, .form-control-file');
                $field.removeClass('o_has_error');
                $controls.removeClass('is-invalid');
                if (invalid_inputs.length || error_fields[field_name]) {
                    $field.addClass('o_has_error');
                    $controls.addClass('is-invalid');
                    if (_.isString(error_fields[field_name])) {
                        $field.popover({content: error_fields[field_name], trigger: 'hover', container: 'body', placement: 'top'});
                        // update error message and show it.
                        $field.data("bs.popover").config.content = error_fields[field_name];
                        $field.popover('show');
                    }
                    form_valid = false;
                }
            });
            return form_valid;
        },

        is_datetime_valid: function (value, type_of_date) {
            if (value === "") {
                return true;
            } else {
                try {
                    this.parse_date(value, type_of_date);
                    return true;
                } catch (e) {
                    return false;
                }
            }
        },

        // This is a stripped down version of format.js parse_value function
        parse_date: function (value, type_of_date, value_if_empty) {
            var date_pattern = time.getLangDateFormat(),
                time_pattern = time.getLangTimeFormat();
            var date_pattern_wo_zero = date_pattern.replace('MM', 'M').replace('DD', 'D'),
                time_pattern_wo_zero = time_pattern.replace('HH', 'H').replace('mm', 'm').replace('ss', 's');
            switch (type_of_date) {
                case 'datetime':
                    var datetime = moment(value, [date_pattern + ' ' + time_pattern, date_pattern_wo_zero + ' ' + time_pattern_wo_zero], true);
                    if (datetime.isValid()) {
                        return time.datetime_to_str(datetime.toDate());
                    }
                    throw new Error(_.str.sprintf(_t("'%s' is not a correct datetime"), value));
                case 'date':
                    var date = moment(value, [date_pattern, date_pattern_wo_zero], true);
                    if (date.isValid()) {
                        return time.date_to_str(date.toDate());
                    }
                    throw new Error(_.str.sprintf(_t("'%s' is not a correct date"), value));
            }
            return value;
        },

        update_status: function (status, message) {
            if (status !== 'success') { // Restore send button behavior if result is an error
                this.$target.find('.s_website_form_send, .o_website_form_send')
                    .removeAttr('disabled')
                    .removeClass('disabled'); // !compatibility
                this.restoreBtnLoading();
            }
            var $result = this.$('#s_website_form_result, #o_website_form_result'); // !compatibility

            if (status === 'error' && !message) {
                message = _t("An error has occured, the form has not been sent.");
            }

            // Note: we still need to wait that the widget is properly started
            // before any qweb rendering which depends on xmlDependencies
            // because the event handlers are binded before the call to
            // willStart for public widgets...
            this.__started.then(() => $result.replaceWith(qweb.render(`website.s_website_form_status_${status}`, {
                message: message,
            })));
        },

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * Gets the user's field needed to be fetched to pre-fill the form.
         *
         * @returns {string[]} List of user's field that have to be fetched.
         */
        _getUserPreFillFields() {
            return ['name', 'phone', 'email', 'commercial_company_name'];
        },
        /**
         * Compares the value with the comparable (and the between) with
         * comparator as a means to compare
         *
         * @private
         * @param {string} comparator The way that $value and $comparable have
         *      to be compared
         * @param {string} [value] The value of the field
         * @param {string} [comparable] The value to compare
         * @param {string} [between] The maximum date value in case comparator
         *      is between or !between
         * @returns {boolean}
         */
        _compareTo(comparator, value = '', comparable, between) {
            switch (comparator) {
                case 'contains':
                    return value.includes(comparable);
                case '!contains':
                    return !value.includes(comparable);
                case 'equal':
                case 'selected':
                    return value === comparable;
                case '!equal':
                case '!selected':
                    return value !== comparable;
                case 'set':
                    return value;
                case '!set':
                    return !value;
                case 'greater':
                    return value > comparable;
                case 'less':
                    return value < comparable;
                case 'greater or equal':
                    return value >= comparable;
                case 'less or equal':
                    return value <= comparable;
                case 'fileSet':
                    return value.name !== '';
                case '!fileSet':
                    return value.name === '';
            }
            // Date & Date Time comparison requires formatting the value
            if (value.includes(':')) {
                const datetimeFormat = time.getLangDatetimeFormat();
                value = moment(value, datetimeFormat)._d.getTime() / 1000;
            } else {
                const dateFormat = time.getLangDateFormat();
                value = moment(value, dateFormat)._d.getTime() / 1000;
            }
            comparable = parseInt(comparable);
            between = parseInt(between) || '';
            switch (comparator) {
                case 'dateEqual':
                    return value === comparable;
                case 'date!equal':
                    return value !== comparable;
                case 'before':
                    return value < comparable;
                case 'after':
                    return value > comparable;
                case 'equal or before':
                    return value <= comparable;
                case 'between':
                    return value >= comparable && value <= between;
                case '!between':
                    return !(value >= comparable && value <= between);
                case 'equal or after':
                    return value >= comparable;
            }
        },
        /**
         * @private
         * @param {HTMLElement} fieldEl the field we want to have a function
         *      that calculates its visibility
         * @returns {function} the function to be executed when we want to
         *      recalculate the visibility of fieldEl
         */
        _buildVisibilityFunction(fieldEl) {
            const visibilityCondition = fieldEl.dataset.visibilityCondition;
            const dependencyName = fieldEl.dataset.visibilityDependency;
            const comparator = fieldEl.dataset.visibilityComparator;
            const between = fieldEl.dataset.visibilityBetween;
            return () => {
                // To be visible, at least one field with the dependency name must be visible.
                const dependencyVisibilityFunction = this._visibilityFunctionByFieldName.get(dependencyName);
                const dependencyIsVisible = !dependencyVisibilityFunction || dependencyVisibilityFunction();
                if (!dependencyIsVisible) {
                    return false;
                }

                const formData = new FormData(this.$target[0]);
                const currentValueOfDependency = formData.get(dependencyName);
                return this._compareTo(comparator, currentValueOfDependency, visibilityCondition, between);
            };
        },
        /**
         * Calculates the visibility for each field with conditional visibility
         */
        _updateFieldsVisibility() {
            for (const [fieldEl, visibilityFunction] of this._visibilityFunctionByFieldEl.entries()) {
                this._updateFieldVisibility(fieldEl, visibilityFunction());
            }
        },
        /**
         * Changes the visibility of a field.
         *
         * @param {HTMLElement} fieldEl
         * @param {boolean} haveToBeVisible
         */
        _updateFieldVisibility(fieldEl, haveToBeVisible) {
            const fieldContainerEl = fieldEl.closest('.s_website_form_field');
            fieldContainerEl.classList.toggle('d-none', !haveToBeVisible);
            for (const inputEl of fieldContainerEl.querySelectorAll('.s_website_form_input')) {
                // Hidden inputs should also be disabled so that their data are
                // not sent on form submit.
                inputEl.disabled = !haveToBeVisible;
            }
        },

        //----------------------------------------------------------------------
        // Handlers
        //----------------------------------------------------------------------

        /**
         * Calculates the visibility of the fields at each input event on the
         * form (this method should be debounced in the start).
         */
        _onFieldInput() {
            this._updateFieldsVisibility();
        },
    });
});
