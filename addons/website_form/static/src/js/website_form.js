odoo.define('website_form.animation', function (require) {
'use strict';

    var core = require('web.core');
    var time = require('web.time');
    var ajax = require('web.ajax');
    var publicWidget = require('web.public.widget');

    var _t = core._t;
    var qweb = core.qweb;

    publicWidget.registry.form_builder_send = publicWidget.Widget.extend({
        selector: '.s_website_form',

        willStart: function () {
            var prom;
            if (!$.fn.datetimepicker) {
                prom = ajax.loadJS("/web/static/lib/tempusdominus/tempusdominus.js");
            }
            return Promise.all([this._super.apply(this, arguments), prom]);
        },

        start: function (editable_mode) {
            if (editable_mode) {
                this.stop();
                return;
            }
            var self = this;
            this.templates_loaded = ajax.loadXML('/website_form/static/src/xml/website_form.xml', qweb);
            this.$target.find('.o_website_form_send').on('click',function (e) {self.send(e);});

            // Initialize datetimepickers
            var l10n = _t.database.parameters;
            var datepickers_options = {
                minDate: moment({ y: 1900 }),
                maxDate: moment().add(200, "y"),
                calendarWeeks: true,
                icons : {
                    time: 'fa fa-clock-o',
                    date: 'fa fa-calendar',
                    next: 'fa fa-chevron-right',
                    previous: 'fa fa-chevron-left',
                    up: 'fa fa-chevron-up',
                    down: 'fa fa-chevron-down',
                   },
                locale : moment.locale(),
                format : time.getLangDatetimeFormat(),
            };
            this.$target.find('.o_website_form_datetime').datetimepicker(datepickers_options);

            // Adapt options to date-only pickers
            datepickers_options.format = time.getLangDateFormat();
            this.$target.find('.o_website_form_date').datetimepicker(datepickers_options);

            // Display form values from tag having data-for attribute
            // It's necessary to handle field values generated on server-side
            // Because, using t-att- inside form make it non-editable
            var $values = $('[data-for=' + this.$target.attr('id') + ']');
            if ($values.length) {
                var values = JSON.parse($values.data('values').replace(/'/g, '"'));
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

            return this._super.apply(this, arguments);
        },

        destroy: function () {
            this._super.apply(this, arguments);
            this.$target.find('button').off('click');
        },

        send: function (e) {
            e.preventDefault();  // Prevent the default submit behavior
            this.$target.find('.o_website_form_send').off().addClass('disabled');  // Prevent users from crazy clicking

            var self = this;

            self.$target.find('#o_website_form_result').empty();
            if (!self.check_error_fields({})) {
                self.update_status('invalid');
                return false;
            }

            // Prepare form inputs
            this.form_fields = this.$target.serializeArray();
            _.each(this.$target.find('input[type=file]'), function (input) {
                $.each($(input).prop('files'), function (index, file) {
                    // Index field name as ajax won't accept arrays of files
                    // when aggregating multiple files into a single field value
                    self.form_fields.push({
                        name: input.name + '[' + index + ']',
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

            // Post form and handle result
            ajax.post(this.$target.attr('action') + (this.$target.data('force_action')||this.$target.data('model_name')), form_values)
            .then(function (result_data) {
                result_data = JSON.parse(result_data);
                if (!result_data.id) {
                    // Failure, the server didn't return the created record ID
                    self.update_status('error');
                    if (result_data.error_fields) {
                        // If the server return a list of bad fields, show these fields for users
                        self.check_error_fields(result_data.error_fields);
                    }
                } else {
                    // Success, redirect or update status
                    var success_page = self.$target.attr('data-success_page');
                    if (success_page) {
                        $(window.location).attr('href', success_page);
                    }
                    else {
                        self.update_status('success');
                    }

                    // Reset the form
                    self.$target[0].reset();
                }
            })
            .guardedCatch(function (){
                self.update_status('error');
            });
        },

        check_error_fields: function (error_fields) {
            var self = this;
            var form_valid = true;
            // Loop on all fields
            this.$target.find('.form-field').each(function (k, field){
                var $field = $(field);
                var field_name = $field.find('.col-form-label').attr('for');

                // Validate inputs for this field
                var inputs = $field.find('.o_website_form_input:not(#editable_select)');
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
                        var checkboxes = _.filter(inputs, function (input){
                            return input.required && input.type === 'checkbox';
                        });
                        return !_.any(checkboxes, function (checkbox) { return checkbox.checked; });

                    // Special cases for dates and datetimes
                    } else if ($(input).hasClass('o_website_form_date')) {
                        if (!self.is_datetime_valid(input.value, 'date')) {
                            return true;
                        }
                    } else if ($(input).hasClass('o_website_form_datetime')) {
                        if (!self.is_datetime_valid(input.value, 'datetime')) {
                            return true;
                        }
                    }
                    return !input.checkValidity();
                });

                // Update field color if invalid or erroneous
                $field.removeClass('o_has_error').find('.form-control, .custom-select').removeClass('is-invalid');
                if (invalid_inputs.length || error_fields[field_name]){
                    $field.addClass('o_has_error').find('.form-control, .custom-select').addClass('is-invalid')
                    if (_.isString(error_fields[field_name])){
                        $field.popover({content: error_fields[field_name], trigger: 'hover', container: 'body', placement: 'top'});
                        // update error message and show it.
                        $field.data("bs.popover").options.content = error_fields[field_name];
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
            var date_pattern_wo_zero = date_pattern.replace('MM','M').replace('DD','D'),
                time_pattern_wo_zero = time_pattern.replace('HH','H').replace('mm','m').replace('ss','s');
            switch (type_of_date) {
                case 'datetime':
                    var datetime = moment(value, [date_pattern + ' ' + time_pattern, date_pattern_wo_zero + ' ' + time_pattern_wo_zero], true);
                    if (datetime.isValid())
                        return time.datetime_to_str(datetime.toDate());
                    throw new Error(_.str.sprintf(_t("'%s' is not a correct datetime"), value));
                case 'date':
                    var date = moment(value, [date_pattern, date_pattern_wo_zero], true);
                    if (date.isValid())
                        return time.date_to_str(date.toDate());
                    throw new Error(_.str.sprintf(_t("'%s' is not a correct date"), value));
            }
            return value;
        },

        update_status: function (status) {
            var self = this;
            if (status !== 'success') {  // Restore send button behavior if result is an error
                this.$target.find('.o_website_form_send').on('click',function (e) {self.send(e);}).removeClass('disabled');
            }
            var $result = this.$('#o_website_form_result');
            this.templates_loaded.then(function () {
                $result.replaceWith(qweb.render("website_form.status_" + status));
            });
        },
    });
});
