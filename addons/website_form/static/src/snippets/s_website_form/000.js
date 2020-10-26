odoo.define('website_form.s_website_form', function (require) {
    'use strict';

    var core = require('web.core');
    var time = require('web.time');
    const {ReCaptcha} = require('google_recaptcha.ReCaptchaV3');
    var ajax = require('web.ajax');
    var publicWidget = require('web.public.widget');

    var _t = core._t;
    var qweb = core.qweb;

    publicWidget.registry.s_website_form = publicWidget.Widget.extend({
        selector: '.s_website_form form, form.s_website_form', // !compatibility
        xmlDependencies: ['/website_form/static/src/xml/website_form.xml'],
        events: {
            'click .s_website_form_send, .o_website_form_send': 'send', // !compatibility
        },

        /**
         * @constructor
         */
        init: function () {
            this._super(...arguments);
            this._recaptcha = new ReCaptcha();
            this.__started = new Promise(resolve => this.__startResolve = resolve);
        },
        willStart: function () {
            const res = this._super(...arguments);
            if (!this.$target[0].classList.contains('s_website_form_no_recaptcha')) {
                this._recaptcha.loadLibs();
            }
            return res;
        },
        start: function () {
            var self = this;

            // Initialize datetimepickers
            var datepickers_options = {
                minDate: moment({ y: 1 }),
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
            };
            this.$target.find('.s_website_form_datetime, .o_website_form_datetime').datetimepicker(datepickers_options); // !compatibility

            // Adapt options to date-only pickers
            datepickers_options.format = time.getLangDateFormat();
            this.$target.find('.s_website_form_date, .o_website_form_date').datetimepicker(datepickers_options); // !compatibility

            // Display form values from tag having data-for attribute
            // It's necessary to handle field values generated on server-side
            // Because, using t-att- inside form make it non-editable
            var $values = $('[data-for=' + this.$target.attr('id') + ']');
            if ($values.length) {
                var values = JSON.parse($values.data('values').replace('False', '""').replace('None', '""').replace(/'/g, '"'));
                var fields = _.pluck(this.$target.serializeArray(), 'name');
                _.each(fields, function (field) {
                    if (_.has(values, field)) {
                        var $field = self.$target.find('input[name="' + field + '"], textarea[name="' + field + '"]');
                        if (!$field.val()) {
                            $field.val(values[field]);
                        }
                    }
                });
            }

            return this._super(...arguments).then(() => this.__startResolve());
        },

        destroy: function () {
            this._super.apply(this, arguments);
            this.$target.find('button').off('click');

            // Empty imputs
            this.$target[0].reset();

            // Remove saving of the error colors
            this.$target.find('.o_has_error').removeClass('o_has_error').find('.form-control, .custom-select').removeClass('is-invalid');

            // Remove the status message
            this.$target.find('#s_website_form_result, #o_website_form_result').empty(); // !compatibility

            // Remove the success message and display the form
            this.$target.removeClass('d-none');
            this.$target.parent().find('.s_website_form_end_message').addClass('d-none');
        },

        send: async function (e) {
            e.preventDefault(); // Prevent the default submit behavior
             // Prevent users from crazy clicking
            this.$target.find('.s_website_form_send, .o_website_form_send')
                .addClass('disabled')    // !compatibility
                .attr('disabled', 'disabled');

            var self = this;

            self.$target.find('#s_website_form_result, #o_website_form_result').empty(); // !compatibility
            if (!self.check_error_fields({})) {
                self.update_status('error', _t("Please fill in the form correctly."));
                return false;
            }

            // Prepare form inputs
            this.form_fields = this.$target.serializeArray();
            $.each(this.$target.find('input[type=file]'), function (outer_index, input) {
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

            const tokenObj = await this._recaptcha.getToken('website_form');
            if (tokenObj.token) {
                form_values['recaptcha_token_response'] = tokenObj.token;
            } else if (tokenObj.error) {
                self.update_status('error', tokenObj.error);
                return false;
            }
            // Post form and handle result
            ajax.post(this.$target.attr('action') + (this.$target.data('force_action') || this.$target.data('model_name')), form_values)
            .then(function (result_data) {
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
                        case 'redirect':
                            $(window.location).attr('href', successPage);
                            break;
                        case 'message':
                            self.$target[0].classList.add('d-none');
                            self.$target[0].parentElement.querySelector('.s_website_form_end_message').classList.remove('d-none');
                            break;
                        default:
                            self.update_status('success');
                            break;
                    }

                    // Reset the form
                    self.$target[0].reset();
                }
            })
            .guardedCatch(function () {
                self.update_status('error');
            });
        },

        check_error_fields: function (error_fields) {
            var self = this;
            var form_valid = true;
            // Loop on all fields
            this.$target.find('.form-field, .s_website_form_field').each(function (k, field) { // !compatibility
                var $field = $(field);
                var field_name = $field.find('.col-form-label').attr('for');

                // Validate inputs for this field
                var inputs = $field.find('.s_website_form_input, .o_website_form_input').not('#editable_select'); // !compatibility
                var invalid_inputs = inputs.toArray().filter(function (input, k, inputs) {
                    // Special check for multiple required checkbox for same
                    // field as it seems checkValidity forces every required
                    // checkbox to be checked, instead of looking at other
                    // checkboxes with the same name and only requiring one
                    // of them to be checked.
                    if (input.required && input.type === 'checkbox') {
                        // Considering we are currently processing a single
                        // field, we can assume that all checkboxes in the
                        // inputs variable have the same name
                        var checkboxes = _.filter(inputs, function (input) {
                            return input.required && input.type === 'checkbox';
                        });
                        return !_.any(checkboxes, checkbox => checkbox.checked);

                    // Special cases for dates and datetimes
                    } else if ($(input).hasClass('s_website_form_date') || $(input).hasClass('o_website_form_date')) { // !compatibility
                        if (!self.is_datetime_valid(input.value, 'date')) {
                            return true;
                        }
                    } else if ($(input).hasClass('s_website_form_datetime') || $(input).hasClass('o_website_form_datetime')) { // !compatibility
                        if (!self.is_datetime_valid(input.value, 'datetime')) {
                            return true;
                        }
                    }
                    return !input.checkValidity();
                });

                // Update field color if invalid or erroneous
                $field.removeClass('o_has_error').find('.form-control, .custom-select').removeClass('is-invalid');
                if (invalid_inputs.length || error_fields[field_name]) {
                    $field.addClass('o_has_error').find('.form-control, .custom-select').addClass('is-invalid');
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
            }
            var $result = this.$('#s_website_form_result, #o_website_form_result'); // !compatibility

            if (status === 'error' && !message) {
                message = _t("An error has occured, the form has not been sent.");
            }

            // Note: we still need to wait that the widget is properly started
            // before any qweb rendering which depends on xmlDependencies
            // because the event handlers are binded before the call to
            // willStart for public widgets...
            this.__started.then(() => $result.replaceWith(qweb.render(`website_form.status_${status}`, {
                message: message,
            })));
        },
    });
});
