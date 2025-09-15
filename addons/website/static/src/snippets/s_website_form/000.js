/** @odoo-module **/

    import {ReCaptcha} from "@google_recaptcha/js/recaptcha";
    import { session } from "@web/session";
    import publicWidget from "@web/legacy/js/public/public_widget";
    import dom from "@web/legacy/js/core/dom";
    import { delay } from "@web/core/utils/concurrency";
    import { debounce } from "@web/core/utils/timing";
    import { _t } from "@web/core/l10n/translation";
    import { renderToElement } from "@web/core/utils/render";
    import { post } from "@web/core/network/http_service";
    import { localization } from "@web/core/l10n/localization";
import {
    formatDate,
    formatDateTime,
    parseDate,
    parseDateTime,
    serializeDate,
    serializeDateTime,
} from "@web/core/l10n/dates";
const { DateTime } = luxon;
import wUtils from '@website/js/utils';

    publicWidget.registry.EditModeWebsiteForm = publicWidget.Widget.extend({
        selector: '.s_website_form form, form.s_website_form', // !compatibility
        disabledInEditableMode: false,
        /**
         * @override
         */
        start: function () {
            if (this.editableMode) {
                // We do not initialize the datetime picker in edit mode but want the dates to be formated
                this.el.querySelectorAll('.s_website_form_input.datetimepicker-input').forEach(el => {
                    const value = el.getAttribute('value');
                    if (value) {
                    const format =
                        el.closest(".s_website_form_field").dataset.type === "date"
                            ? formatDate
                            : formatDateTime;
                        el.value = format(DateTime.fromSeconds(parseInt(value)));
                    }
                });
            }
            return this._super(...arguments);
        },
        // Todo: remove in master
        /**
         * @private
         */
        _getDataForFields() {
            if (!this.dataForValues) {
                return [];
            }
            return Object.keys(this.dataForValues)
                .map(name => this.$target[0].querySelector(`[name="${CSS.escape(name)}"]`))
                .filter(dataForValuesFieldEl => dataForValuesFieldEl && dataForValuesFieldEl.name !== "email_to");
        }
    });

    publicWidget.registry.s_website_form = publicWidget.Widget.extend({
        selector: '.s_website_form form, form.s_website_form', // !compatibility
        events: {
            'click .s_website_form_send, .o_website_form_send': 'send', // !compatibility
            'submit': 'send',
            "change input[type=file]": "_onFileChange",
            "click input.o_add_files_button": "_onAddFilesButtonClick",
            "click .o_file_delete": "_onFileDeleteClick",
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
            this.orm = this.bindService("orm");
        },
        willStart: async function () {
            const res = this._super(...arguments);
            if (!this.el.classList.contains('s_website_form_no_recaptcha')) {
                this._recaptchaLoaded = true;
                this._recaptcha.loadLibs();
            }
            // fetch user data (required by fill-with behavior)
            this.preFillValues = {};
            if (session.user_id) {
                this.preFillValues = (await this.orm.read(
                    "res.users",
                    [session.user_id],
                    this._getUserPreFillFields()
                ))[0] || {};
            }
            return res;
        },
        start: function () {
            // Reset the form first, as it is still filled when coming back
            // after a redirect.
            this.resetForm();

            // Prepare visibility data and update field visibilities
            const visibilityFunctionsByFieldName = new Map();
            for (const fieldEl of this.el.querySelectorAll('[data-visibility-dependency]')) {
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

            this._onFieldInputDebounced = debounce(this._onFieldInput.bind(this), 400);
            this.$el.on('input.s_website_form', '.s_website_form_field', this._onFieldInputDebounced);

            this.$allDates = this.$el.find('.s_website_form_datetime, .o_website_form_datetime, .s_website_form_date, .o_website_form_date');
            for (const field of this.$allDates) {
                const input = field.querySelector("input");
                const defaultValue = input.getAttribute("value");
                this.call("datetime_picker", "create", {
                    target: input,
                    onChange: () => input.dispatchEvent(new Event("input", { bubbles: true })),
                    pickerProps: {
                        type: field.matches('.s_website_form_date, .o_website_form_date') ? 'date' : 'datetime',
                        value: defaultValue && DateTime.fromSeconds(parseInt(defaultValue)),
                    },
                }).enable();
            }
            this.$allDates.addClass('s_website_form_datepicker_initialized');

            // Display form values from tag having data-for attribute
            // It's necessary to handle field values generated on server-side
            // Because, using t-att- inside form make it non-editable
            // Data-fill-with attribute is given during registry and is used by
            // to know which user data should be used to prfill fields.
            let dataForValues = wUtils.getParsedDataFor(this.el.id, document);
            this.editTranslations = !!this._getContext(true).edit_translations;
            // On the "edit_translations" mode, a <span/> with a translated term
            // will replace the attribute value, leading to some inconsistencies
            // (setting again the <span> on the attributes after the editor's
            // cleanup, setting wrong values on the attributes after translating
            // default values...)
            if (!this.editTranslations
                    && (dataForValues || Object.keys(this.preFillValues).length)) {
                dataForValues = dataForValues || {};
                const fieldNames = this.$target.serializeArray().map(el => el.name);
                // All types of inputs do not have a value property (eg:hidden),
                // for these inputs any function that is supposed to put a value
                // property actually puts a HTML value attribute. Because of
                // this, we have to clean up these values at destroy or else the
                // data loaded here could become default values. We could set
                // the values to submit() for these fields but this could break
                // customizations that use the current behavior as a feature.
                for (const name of fieldNames) {
                    const fieldEl = this.el.querySelector(`[name="${CSS.escape(name)}"]`);

                    // In general, we want the data-for and prefill values to
                    // take priority over set default values. The 'email_to'
                    // field is however treated as an exception at the moment
                    // so that values set by users are always used.
                    if (name === 'email_to' && fieldEl.value
                            // The following value is the default value that
                            // is set if the form is edited in any way. (see the
                            // @website/js/form_editor_registry module in editor
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
            this._updateFieldsVisibility();

            if (session.geoip_phone_code) {
                this.el.querySelectorAll('input[type="tel"]').forEach(telField => {
                    if (!telField.value) {
                        telField.value = '+' + session.geoip_phone_code;
                    }
                });
            }
            // Check disabled states
            this.inputEls = this.el.querySelectorAll('.s_website_form_field.s_website_form_field_hidden_if .s_website_form_input');
            this._disabledStates = new Map();
            for (const inputEl of this.inputEls) {
                this._disabledStates[inputEl] = inputEl.disabled;
            }

            // Add the files zones where the file blocks will be displayed.
            this.el.querySelectorAll("input[type=file]").forEach(inputEl => {
                const filesZoneEl = document.createElement("DIV");
                filesZoneEl.classList.add("o_files_zone", "row", "gx-1");
                inputEl.parentNode.insertBefore(filesZoneEl, inputEl);
            });

            return this._super(...arguments).then(() => this.__startResolve());
        },

        destroy: function () {
            this._super.apply(this, arguments);
            this.$el.find('button').off('click');

            // Empty inputs
            this.resetForm();

            // Apply default values
            this.el.querySelectorAll('input[type="text"], input[type="email"], input[type="number"]').forEach(el => {
                let value = el.getAttribute('value');
                if (value) {
                    if (el.classList.contains('datetimepicker-input')) {
                        const format =
                            el.closest(".s_website_form_field").dataset.type === "date"
                                ? formatDate
                                : formatDateTime;
                        value = format(DateTime.fromSeconds(parseInt(value)));
                    }
                    el.value = value;
                }
            });
            this.el.querySelectorAll('textarea').forEach(el => el.value = el.textContent);

            // Remove saving of the error colors
            this.$el.find('.o_has_error').removeClass('o_has_error').find('.form-control, .form-select').removeClass('is-invalid');

            // Remove the status message
            this.$el.find('#s_website_form_result, #o_website_form_result').empty(); // !compatibility

            // Remove the success message and display the form
            this.$el.removeClass('d-none');
            this.$el.parent().find('.s_website_form_end_message').addClass('d-none');

            // Reinitialize dates
            this.$allDates.removeClass('s_website_form_datepicker_initialized');

            // Restore disabled attribute
            for (const inputEl of this.inputEls) {
                inputEl.disabled = !!this._disabledStates.get(inputEl);
            }

            // All 'hidden if' fields start with d-none
            this.el.querySelectorAll('.s_website_form_field_hidden_if:not(.d-none)').forEach(el => el.classList.add('d-none'));

            // Prevent "data-for" values removal on destroy, they are still used
            // in edit mode to keep the form linked to its predefined server
            // values (e.g., the default `job_id` value on the application form
            // for a given job).
            const dataForValues = wUtils.getParsedDataFor(this.$target[0].id, document) || {};
            const initialValuesToReset = new Map(
                [...this.initialValues.entries()].filter(
                    ([input]) => !dataForValues[input.name] || input.name === "email_to"
                )
            );
            // Reset the initial default values.
            for (const [fieldEl, initialValue] of initialValuesToReset.entries()) {
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
            const $button = this.$el.find('.s_website_form_send, .o_website_form_send');
            $button.addClass('disabled') // !compatibility
                   .attr('disabled', 'disabled');
            this.restoreBtnLoading = dom.addButtonLoadingEffect($button[0]);

            var self = this;

            self.$el.find('#s_website_form_result, #o_website_form_result').empty(); // !compatibility
            if (!self.check_error_fields({})) {
                if (this.fileInputError) {
                    const errorMessage = this.fileInputError.type === "number"
                        ? _t(
                            "Please fill in the form correctly. You uploaded too many files. (Maximum %s files)", 
                            this.fileInputError.limit
                        )
                        : _t(
                            "Please fill in the form correctly. The file \"%s\" is too big. (Maximum %s MB)", 
                            this.fileInputError.fileName,
                            this.fileInputError.limit
                        );
                    this.update_status("error", errorMessage);
                    delete this.fileInputError;
                } else {
                    this.update_status("error", _t("Please fill in the form correctly."));
                }
                return false;
            }

            // Prepare form inputs
            this.form_fields = this.$el.serializeArray();
            $.each(this.$el.find('input[type=file]:not([disabled])'), (outer_index, input) => {
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
            this.form_fields.forEach((input) => {
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
            this.$el.find('.s_website_form_field:not(.s_website_form_custom)')
            .find('.s_website_form_date, .s_website_form_datetime').each(function () {
                const inputEl = this.querySelector('input');
                const { value } = inputEl;
                if (!value) {
                    return;
                }

                form_values[inputEl.getAttribute("name")] = this.matches(".s_website_form_date")
                    ? serializeDate(parseDate(value))
                    : serializeDateTime(parseDateTime(value));
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

            if (odoo.csrf_token) {
                form_values.csrf_token = odoo.csrf_token;
            }

            const formData = new FormData();
            for (const [key, value] of Object.entries(form_values)) {
                formData.append(key, value);
            }

            // Post form and handle result
            post(this.$el.attr('action') + (this.$el.data('force_action') || this.$el.data('model_name')), formData)
            .then(async function (result_data) {
                // Restore send button behavior
                self.$el.find('.s_website_form_send, .o_website_form_send')
                    .removeAttr('disabled')
                    .removeClass('disabled'); // !compatibility
                if (!result_data.id) {
                    // Failure, the server didn't return the created record ID
                    self.update_status('error', result_data.error ? result_data.error : false);
                    if (result_data.error_fields) {
                        // If the server return a list of bad fields, show these fields for users
                        self.check_error_fields(result_data.error_fields);
                    }
                } else {
                    // Success, redirect or update status
                    let successMode = self.el.dataset.successMode;
                    let successPage = self.el.dataset.successPage;
                    if (!successMode) {
                        successPage = self.$el.attr('data-success_page'); // Compatibility
                        successMode = successPage ? 'redirect' : 'nothing';
                    }
                    switch (successMode) {
                        case 'redirect': {
                            let hashIndex = successPage.indexOf("#");
                            if (hashIndex > 0) {
                                // URL containing an anchor detected: extract
                                // the anchor from the URL if the URL is the
                                // same as the current page URL so we can scroll
                                // directly to the element (if found) later
                                // instead of redirecting.
                                // Note that both currentUrlPath and successPage
                                // can exist with or without a trailing slash
                                // before the hash (e.g. "domain.com#footer" or
                                // "domain.com/#footer"). Therefore, if they are
                                // not present, we add them to be able to
                                // compare the two variables correctly.
                                let currentUrlPath = window.location.pathname;
                                if (!currentUrlPath.endsWith("/")) {
                                    currentUrlPath = currentUrlPath + "/";
                                }
                                if (!successPage.includes("/#")) {
                                    successPage = successPage.replace("#", "/#");
                                    hashIndex++;
                                }
                                if ([successPage, "/" + session.lang_url_code + successPage].some(link => link.startsWith(currentUrlPath + '#'))) {
                                    successPage = successPage.substring(hashIndex);
                                }
                            }
                            if (successPage.charAt(0) === "#") {
                                const successAnchorEl = document.getElementById(successPage.substring(1));
                                if (successAnchorEl) {
                                    // Check if the target of the link is a modal.
                                    if (successAnchorEl.classList.contains("modal")) {
                                        // Trigger a "hashChange" event to
                                        // notify the popup widget to show the
                                        // popup.
                                        window.location.href = successPage;
                                    } else {
                                        await dom.scrollTo(successAnchorEl, {
                                            duration: 500,
                                            extraOffset: 0,
                                        });
                                    }
                                }
                                break;
                            }
                            $(window.location).attr('href', successPage);
                            return;
                        }
                        case 'message': {
                            // Prevent double-clicking on the send button and
                            // add a upload loading effect (delay before success
                            // message)
                            await delay(dom.DEBOUNCE);

                            self.el.classList.add('d-none');
                            self.el.parentElement.querySelector('.s_website_form_end_message').classList.remove('d-none');
                            break;
                        }
                        default: {
                            // Prevent double-clicking on the send button and
                            // add a upload loading effect (delay before success
                            // message)
                            await delay(dom.DEBOUNCE);

                            self.update_status('success');
                            break;
                        }
                    }

                    self.resetForm();
                    self.restoreBtnLoading();
                }
            })
            .catch(error => {
                this.update_status(
                    'error',
                    error.status && error.status === 413 ? _t("Uploaded file is too large.") : "",
                );
            });
        },

        /**
         * Resets a form.
         */
        resetForm() {
            this.el.reset();

            // For file inputs, remove the files zone, restore the file input
            // and remove the files list.
            this.el.querySelectorAll("input[type=file]").forEach(inputEl => {
                const fieldEl = inputEl.closest(".s_website_form_field");
                fieldEl.querySelectorAll(".o_files_zone").forEach(el => el.remove());
                fieldEl.querySelectorAll(".o_add_files_button").forEach(el => el.remove());
                inputEl.classList.remove("d-none");
                delete inputEl.fileList;
            });
        },

        check_error_fields: function (error_fields) {
            var self = this;
            var form_valid = true;
            // Loop on all fields
            this.$el.find('.form-field, .s_website_form_field').each(function (k, field) { // !compatibility
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
                        var checkboxes = inputs.filter(input => input.required && input.type === 'checkbox');
                        return !checkboxes.some((checkbox) => checkbox.checkValidity());

                    // Special cases for dates and datetimes
                    // FIXME this seems like dead code, the inputs do not use
                    // those classes, their parent does (but it seemed to work
                    // at some point given that https://github.com/odoo/odoo/commit/75e03c0f7692a112e1b0fa33267f4939363f3871
                    // was made)... need more investigation (if restored,
                    // consider checking the date inputs are not disabled before
                    // saying they are invalid (see checkValidity used here))
                    } else if ($(input).hasClass('s_website_form_date') || $(input).hasClass('o_website_form_date')) { // !compatibility
                        const date = parseDate(input.value);
                        if (!date || !date.isValid) {
                            return true;
                        }
                    } else if ($(input).hasClass('s_website_form_datetime') || $(input).hasClass('o_website_form_datetime')) { // !compatibility
                        const date = parseDateTime(input.value);
                        if (!date || !date.isValid) {
                            return true;
                        }
                    } else if (input.type === "file" && !self.isFileInputValid(input)) {
                        return true;
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
                const $controls = $field.find('.form-control, .form-select, .form-check-input');
                $field.removeClass('o_has_error');
                $controls.removeClass('is-invalid');
                if (invalid_inputs.length || error_fields[field_name]) {
                    $field.addClass('o_has_error');
                    $controls.addClass('is-invalid');
                    if (typeof error_fields[field_name] === "string") {
                        $field.popover({content: error_fields[field_name], trigger: 'hover', container: 'body', placement: 'top'});
                        // update error message and show it.
                        const popover = Popover.getInstance($field);
                        popover._config.content = error_fields[field_name];
                        $field.popover('show');
                    }
                    form_valid = false;
                }
            });
            return form_valid;
        },

        update_status: function (status, message) {
            if (status !== 'success') { // Restore send button behavior if result is an error
                this.$el.find('.s_website_form_send, .o_website_form_send')
                    .removeAttr('disabled')
                    .removeClass('disabled'); // !compatibility
                this.restoreBtnLoading();
            }
            var $result = this.$('#s_website_form_result, #o_website_form_result'); // !compatibility

            if (status === 'error' && !message) {
                message = _t("An error has occured, the form has not been sent.");
            }

            // Note: we still need to wait that the widget is properly started
            // before any qweb rendering which depends on xml assets
            // because the event handlers are binded before the call to
            // willStart for public widgets...
            this.__started.then(() => $result.replaceWith(renderToElement(`website.s_website_form_status_${status}`, {
                message: message,
            })));
        },

        /**
         * Checks if the file input is valid: if the number of files uploaded
         * and their size do not exceed the limits that were set.
         *
         * @param {HTMLElement} inputEl an input of type file
         * @returns {Boolean} true if the input is valid, false otherwise.
         */
        isFileInputValid(inputEl) {
            // Note: the `maxFilesNumber` and `maxFileSize` data-attributes may
            // not always be present, if the Form comes from an older version
            // for example.

            // Checking the number of files.
            const maxFilesNumber = inputEl.dataset.maxFilesNumber;
            if (maxFilesNumber && inputEl.files.length > maxFilesNumber) {
                // Store information to display the error message later.
                this.fileInputError = {type: "number", limit: maxFilesNumber};
                return false;
            }
            // Checking the files size.
            const maxFileSize = inputEl.dataset.maxFileSize; // in megabytes.
            const bytesInMegabyte = 1_000_000;
            if (maxFileSize) {
                for (const file of Object.values(inputEl.files)) {
                    if (file.size / bytesInMegabyte > maxFileSize) {
                        this.fileInputError = {type: "size", limit: maxFileSize, fileName: file.name};
                        return false;
                    }
                }
            }
            return true;
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
            // Value can be null when the compared field is supposed to be
            // visible, but is not yet retrievable from the FormData() because
            // the field was conditionally hidden. It can be considered empty.
            if (value === null) {
                value = '';
            }

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
                    return parseFloat(value) > parseFloat(comparable);
                case 'less':
                    return parseFloat(value) < parseFloat(comparable);
                case 'greater or equal':
                    return parseFloat(value) >= parseFloat(comparable);
                case 'less or equal':
                    return parseFloat(value) <= parseFloat(comparable);
                case 'fileSet':
                    return value.name !== '';
                case '!fileSet':
                    return value.name === '';
            }

            const format = value.includes(':')
                ? localization.dateTimeFormat
                : localization.dateFormat;
            // Date & Date Time comparison requires formatting the value
            const dateTime = DateTime.fromFormat(value, format);
            // If invalid, any value other than "NaN" would cause certain
            // conditions to be broken.
            value = dateTime.isValid ? dateTime.toUnixInteger() : NaN;

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

                const formData = new FormData(this.el);
                const currentValueOfDependency = ["contains", "!contains"].includes(comparator)
                    ? formData.getAll(dependencyName).join()
                    : formData.get(dependencyName);
                return this._compareTo(comparator, currentValueOfDependency, visibilityCondition, between);
            };
        },
        /**
         * Calculates the visibility for each field with conditional visibility
         */
        _updateFieldsVisibility() {
            let anyFieldVisibilityUpdated = false;
            for (const [fieldEl, visibilityFunction] of this._visibilityFunctionByFieldEl.entries()) {
                const wasVisible = !fieldEl.closest(".s_website_form_field")
                    .classList.contains("d-none");
                const isVisible = !!visibilityFunction();
                this._updateFieldVisibility(fieldEl, isVisible);
                anyFieldVisibilityUpdated |= wasVisible !== isVisible;
            }
            // Recursive check needed in case of a field (C) that
            // conditionally displays a prefilled field (B), which in turn
            // triggers a conditional visibility on another field (A),
            // registered before B.
            if (anyFieldVisibilityUpdated) {
                this._updateFieldsVisibility();
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
            // Do not disable inputs that are required for the model.
            if (!fieldContainerEl.matches(".s_website_form_model_required")) {
                for (const inputEl of fieldContainerEl.querySelectorAll(".s_website_form_input")) {
                    // Hidden inputs should also be disabled so that their data are
                    // not sent on form submit.
                    inputEl.disabled = !haveToBeVisible;
                }
            }
        },
        /**
         * Creates a block containing the file name and a cross to delete it.
         *
         * @private
         * @param {Object} fileDetails the details of the file being uploaded
         * @param {HTMLElement} filesZoneEl the zone where the file blocks are
         *      displayed
         */
        _createFileBlock(fileDetails, filesZoneEl) {
            const fileBlockEl = renderToElement("website.file_block", {fileName: fileDetails.name});
            fileBlockEl.fileDetails = fileDetails;
            filesZoneEl.append(fileBlockEl);
        },
        /**
         * Creates the file upload button (= a button to replace the file input,
         * in order to modify its text content more easily).
         *
         * @private
         * @param {HTMLElement} inputEl the file input
         */
        _createAddFilesButton(inputEl) {
            const addFilesButtonEl = document.createElement("INPUT");
            addFilesButtonEl.classList.add("o_add_files_button", "form-control");
            addFilesButtonEl.type = "button";
            addFilesButtonEl.value = inputEl.hasAttribute("multiple")
                ? _t("Add Files") : _t("Replace File");
            inputEl.parentNode.insertBefore(addFilesButtonEl, inputEl);
            inputEl.classList.add("d-none");
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
        /**
         * Called when files are uploaded: updates the button text content,
         * displays the file blocks (containing the files name and a cross to
         * delete them) and manages the files.
         *
         * @private
         * @param {Event} ev
         */
        _onFileChange(ev) {
            const fileInputEl = ev.currentTarget;
            const fieldEl = fileInputEl.closest(".s_website_form_field");
            const uploadedFiles = fileInputEl.files;
            const addFilesButtonEl = fieldEl.querySelector(".o_add_files_button");

            // The zone where the file blocks are displayed.
            let filesZoneEl = fieldEl.querySelector(".o_files_zone");
            // Update the button text content.
            if (!addFilesButtonEl) {
                this._createAddFilesButton(fileInputEl);
            }

            // Create a list to keep track of the files.
            if (!fileInputEl.fileList) {
                fileInputEl.fileList = new DataTransfer();
            }

            // If only one file can be uploaded, delete the previous file.
            if (!fileInputEl.hasAttribute("multiple") && uploadedFiles.length > 0) {
                fileInputEl.fileList = new DataTransfer();
                const fileBlockEl = fieldEl.querySelector(".o_file_block");
                if (fileBlockEl) {
                    fileBlockEl.remove();
                }
            }

            // Add the uploaded files if they are not already there.
            for (const newFile of uploadedFiles) {
                if (![...fileInputEl.fileList.files].some(file => newFile.name === file.name &&
                    newFile.size === file.size && newFile.type === file.type)) {
                    fileInputEl.fileList.items.add(newFile);
                    const fileDetails = {name: newFile.name, size: newFile.size, type: newFile.type};
                    this._createFileBlock(fileDetails, filesZoneEl);
                }
            }
            // Update the input files.
            fileInputEl.files = fileInputEl.fileList.files;
        },
        /**
         * Called when a file is deleted by clicking on the cross on the block
         * describing it.
         *
         * @private
         * @param {Event} ev
         */
        _onFileDeleteClick(ev) {
            const fileBlockEl = ev.target.closest(".o_file_block");
            const fieldEl = fileBlockEl.closest(".s_website_form_field");
            const fileInputEl = fieldEl.querySelector("input[type=file]");
            const fileDetails = fileBlockEl.fileDetails;
            const addFilesButtonEl = fieldEl.querySelector(".o_add_files_button");

            // Create a new file list containing the remaining files.
            const newFileList = new DataTransfer();
            for (const file of Object.values(fileInputEl.fileList.files)) {
                if (file.name !== fileDetails.name || file.size !== fileDetails.size
                    || file.type !== fileDetails.type) {
                    newFileList.items.add(file);
                }
            }
            // Update the input lists and remove the file block.
            Object.assign(fileInputEl, {fileList: newFileList, files: newFileList.files});
            fileBlockEl.remove();

            // Restore the file input if there are no files uploaded and update
            // the fields visibility.
            if (!newFileList.files.length) {
                fileInputEl.classList.remove("d-none");
                addFilesButtonEl.remove();
                this._updateFieldsVisibility();
            }
        },
        /**
         * Detects when the fake input file button is clicked to simulate a
         * click on the real input.
         *
         * @private
         * @param {MouseEvent} ev
         */
        _onAddFilesButtonClick(ev) {
            const fileInputEl = ev.target.parentNode.querySelector("input[type=file]");
            fileInputEl.click();
        },
    });
