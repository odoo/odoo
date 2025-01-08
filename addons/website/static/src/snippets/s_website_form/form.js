import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { ReCaptcha } from "@google_recaptcha/js/recaptcha";
import { localization } from "@web/core/l10n/localization";
import { _t } from "@web/core/l10n/translation";
import { post } from "@web/core/network/http_service";
import { user } from "@web/core/user";
import { delay } from "@web/core/utils/concurrency";
import { session } from "@web/session";
import { addLoadingEffect } from "@web/core/utils/ui";
import {
    formatDate,
    formatDateTime,
    parseDate,
    parseDateTime,
    serializeDate,
    serializeDateTime,
} from "@web/core/l10n/dates";
import { scrollTo } from "@web_editor/js/common/scrolling";
import wUtils from "@website/js/utils";

const { DateTime } = luxon;

export class Form extends Interaction {
    static selector = ".s_website_form form, form.s_website_form"; // !compatibility
    dynamicContent = {
        ".s_website_form_send, .o_website_form_send": { "t-on-click.prevent": this.send }, // !compatibility
        _root: {
            "t-on-submit.prevent": this.send,
            "t-att-class": () => ({
                "d-none": this.isHidden,
            })
        },
        ".s_website_form_end_message": {
            "t-att-class": () => ({
                "d-none": !this.isHidden,
            })
        },
        "input[type=file]": { "t-on-change": this.changeFile },
        "input.o_add_files_button": { "t-on-click": this.clickAddFilesButton },
        ".s_website_form_field[data-type=binary]": { "t-on-click": this.clickFileDelete }, // delegate on ".o_file_delete"
        ".s_website_form_field": {
            "t-on-input": this.onFieldInput,
            "t-att-class": (el) => ({ "d-none": !this.isFieldVisible(el) }),
        },
        ".s_website_form_field .s_website_form_input": {
            "t-att-disabled": (el) => !this.isInputVisible(el) || undefined,
        },
        ".s_website_form_datetime, .o_website_form_datetime, .s_website_form_date, .o_website_form_date": {
            "t-att-class": () => ({
                "s_website_form_datepicker_initialized": this.datapickerInitialized,
            }),
        },
    };

    setup() {
        this.isHidden = false;
        this.datapickersInitialized = false;
        this.recaptcha = new ReCaptcha();
        this.initialValues = new Map();
        this.disabledStates = new Map();
        this.visibilityFunctionByFieldEl = new Map();
        this.visibilityFunctionByFieldName = new Map();
        this.inputEls = this.el.querySelectorAll(".s_website_form_field.s_website_form_field_hidden_if .s_website_form_input");
        this.dateFieldEls = this.el.querySelectorAll(".s_website_form_datetime, .o_website_form_datetime, .s_website_form_date, .o_website_form_date");
        this.disableDateTimePickers = [];
        this.preFillValues = {};
    }

    async willStart() {
        if (!this.el.classList.contains("s_website_form_no_recaptcha")) {
            this.recaptchaLoaded = true;
            await this.recaptcha.loadLibs();
        }
        // fetch user data (required by fill-with behavior)
        if (user.userId) {
            this.preFillValues = (await this.services.orm.read(
                "res.users",
                [user.userId],
                this.getUserPreFillFields()
            ))[0] || {};
        }
        // Reset the form first, as it is still filled when coming back
        // after a redirect.
        this.resetForm();

        // Prepare visibility data and update field visibilities
        const visibilityFunctionsByFieldName = new Map();
        for (const fieldEl of this.el.querySelectorAll("[data-visibility-dependency]")) {
            const inputName = fieldEl.querySelector(".s_website_form_input").name;
            if (!visibilityFunctionsByFieldName.has(inputName)) {
                visibilityFunctionsByFieldName.set(inputName, []);
            }
            const func = this.buildVisibilityFunction(fieldEl);
            visibilityFunctionsByFieldName.get(inputName).push(func);
            this.visibilityFunctionByFieldEl.set(fieldEl, func);
        }
        for (const [name, funcs] of visibilityFunctionsByFieldName.entries()) {
            this.visibilityFunctionByFieldName.set(name, () => funcs.some(func => func()));
        }
    }

    start() {
        this.prepareDateFields();
        this.prefillValues();

        // Visibility might need to be adapted according to pre-filled values.
        this.updateContent();

        if (session.geoip_phone_code) {
            this.el.querySelectorAll(`input[type="tel"]`).forEach(telField => {
                if (!telField.value) {
                    telField.value = "+" + session.geoip_phone_code;
                }
            });
        }
        // Check disabled states
        for (const inputEl of this.inputEls) {
            this.disabledStates[inputEl] = inputEl.disabled;
        }

        // Add the files zones where the file blocks will be displayed.
        this.el.querySelectorAll("input[type=file]").forEach(inputEl => {
            const filesZoneEl = document.createElement("DIV");
            filesZoneEl.classList.add("o_files_zone", "row", "gx-1");
            inputEl.parentNode.insertBefore(filesZoneEl, inputEl);
        });
    }

    destroy() {
        // TODO Find out which event this is about.
        // this.$el.find("button").off("click");

        // Empty inputs
        this.resetForm();

        // Apply default values
        this.el.querySelectorAll(`input[type="text"], input[type="email"], input[type="number"]`).forEach(el => {
            let value = el.getAttribute("value");
            if (value) {
                if (el.classList.contains("datetimepicker-input")) {
                    const format =
                        el.closest(".s_website_form_field").dataset.type === "date"
                            ? formatDate
                            : formatDateTime;
                    value = format(DateTime.fromSeconds(parseInt(value)));
                }
                el.value = value;
            }
        });
        this.el.querySelectorAll("textarea").forEach(el => el.value = el.textContent);

        // Remove saving of the error colors
        for (const errorEl of this.el.querySelectorAll(".o_has_error")) {
            errorEl.classList.remove("o_has_error");
            for (const el of errorEl.querySelectorAll(".form-control, .form-select")) {
                el.classList.remove("is-invalid");
            }
        }

        // Remove the status message
        this.el.querySelector("#s_website_form_result, #o_website_form_result")?.replaceChildren(); // !compatibility

        // Restore disabled attribute
        for (const inputEl of this.inputEls) {
            inputEl.disabled = !!this.disabledStates.get(inputEl);
        }

        // All 'hidden if' fields start with d-none
        this.el.querySelectorAll(".s_website_form_field_hidden_if:not(.d-none)").forEach(el => el.classList.add("d-none"));

        // Reset the initial default values.
        for (const [fieldEl, initialValue] of this.initialValues.entries()) {
            if (initialValue) {
                fieldEl.setAttribute("value", initialValue);
            } else {
                fieldEl.removeAttribute("value");
            }
        }

        for (const disableDateTimePicker of this.disableDateTimePickers) {
            disableDateTimePicker();
        }
    }

    prepareDateFields() {
        for (const fieldEl of this.dateFieldEls) {
            const inputEl = fieldEl.querySelector("input");
            const defaultValue = inputEl.getAttribute("value");
            this.disableDateTimePickers.push(this.services.datetime_picker.create({
                target: inputEl,
                onChange: () => inputEl.dispatchEvent(new Event("input", { bubbles: true })),
                pickerProps: {
                    type: fieldEl.matches(".s_website_form_date, .o_website_form_date") ? "date" : "datetime",
                    value: defaultValue && DateTime.fromSeconds(parseInt(defaultValue)),
                },
            }).enable());
        }
        this.datapickerInitialized = true
    }

    prefillValues() {
        // Display form values from tag having data-for attribute
        // It's necessary to handle field values generated on server-side
        // Because, using t-att- inside form make it non-editable
        // Data-fill-with attribute is given during registry and is used by
        // to know which user data should be used to prfill fields.
        let dataForValues = wUtils.getParsedDataFor(this.el.id, document);
        // On the "edit_translations" mode, a <span/> with a translated term
        // will replace the attribute value, leading to some inconsistencies
        // (setting again the <span> on the attributes after the editor's
        // cleanup, setting wrong values on the attributes after translating
        // default values...)
        if (dataForValues || Object.keys(this.preFillValues).length) {
            dataForValues = dataForValues || {};
            const fieldNames = [...this.el.querySelectorAll("[name]")].map(
                (el) => el.name
            );
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
                if (name === "email_to" && fieldEl.value
                    // The following value is the default value that
                    // is set if the form is edited in any way. (see the
                    // @website/js/form_editor_registry module in editor
                    // assets bundle).
                    // TODO that value should probably never be forced
                    // unless explicitely manipulated by the user or on
                    // custom form addition but that seems risky to
                    // change as a stable fix.
                    && fieldEl.value !== "info@yourcompany.example.com") {
                    continue;
                }

                let newValue;
                if (dataForValues && dataForValues[name]) {
                    newValue = dataForValues[name];
                } else if (this.preFillValues[fieldEl.dataset.fillWith]) {
                    newValue = this.preFillValues[fieldEl.dataset.fillWith];
                }
                if (newValue) {
                    this.initialValues.set(fieldEl, fieldEl.getAttribute("value"));
                    fieldEl.value = newValue;
                }
            }
        }
    }

    async send() {
        // Prevent users from crazy clicking
        const buttonEl = this.el.querySelector(".s_website_form_send, .o_website_form_send");
        buttonEl.classList.add("disabled"); // !compatibility
        buttonEl.setAttribute("disabled", "disabled");
        this.restoreBtnLoading = addLoadingEffect(buttonEl);
        this.el.querySelector("#s_website_form_result, #o_website_form_result").replaceChildren(); // !compatibility
        if (!this.checkErrorFields({})) {
            if (this.fileInputError) {
                const errorMessage = this.fileInputError.type === "number"
                    ? _t(
                        "Please fill in the form correctly. You uploaded too many files. (Maximum %s files)",
                        this.fileInputError.limit
                    )
                    : _t(
                        "Please fill in the form correctly. The file “%(file name)s” is too large. (Maximum %(max)s MB)",
                        { "file name": this.fileInputError.fileName, max: this.fileInputError.limit }
                    );
                this.updateStatus("error", errorMessage);
                delete this.fileInputError;
            } else {
                this.updateStatus("error", _t("Please fill in the form correctly."));
            }
            return false;
        }

        // Prepare form inputs
        const formFields = [];
        new FormData(this.el).forEach((value, key) => {
            formFields.push({ name: key, value: value });
        });
        let outerIndex = 0;
        for (const inputEl of this.el.querySelectorAll("input[type=file]:not([disabled])")) {
            let index = 0;
            for (const file of inputEl.files) {
                // Index field name as ajax won't accept arrays of files
                // when aggregating multiple files into a single field value
                formFields.push({
                    name: `${inputEl.name}[${outerIndex}][${index}]`,
                    value: file,
                });
                index++;
            }
            outerIndex++;
        }

        // Serialize form inputs into a single object
        // Aggregate multiple values into arrays
        const formValues = {};
        formFields.forEach((input) => {
            if (input.name in formValues) {
                // If a value already exists for this field,
                // we are facing a x2many field, so we store
                // the values in an array.
                if (Array.isArray(formValues[input.name])) {
                    formValues[input.name].push(input.value);
                } else {
                    formValues[input.name] = [formValues[input.name], input.value];
                }
            } else {
                if (input.value !== "") {
                    formValues[input.name] = input.value;
                }
            }
        });

        // force server date format usage for existing fields
        for (const fieldEl of this.el.querySelectorAll(".s_website_form_field:not(.s_website_form_custom)")) {
            for (const dateEl of fieldEl.querySelectorAll(".s_website_form_date, .s_website_form_datetime")) {
                const inputEl = dateEl.querySelector("input");
                const { value } = inputEl;
                if (!value) {
                    return;
                }

                formValues[inputEl.getAttribute("name")] = dateEl.matches(".s_website_form_date")
                    ? serializeDate(parseDate(value))
                    : serializeDateTime(parseDateTime(value));
            }
        }

        if (this.recaptchaLoaded) {
            const tokenObj = await this.waitFor(this.recaptcha.getToken("website_form"));
            if (tokenObj.token) {
                formValues["recaptcha_token_response"] = tokenObj.token;
            } else if (tokenObj.error) {
                this.updateStatus("error", tokenObj.error);
                return false;
            }
        }

        if (odoo.csrf_token) {
            formValues.csrf_token = odoo.csrf_token;
        }

        const formData = new FormData();
        for (const [key, value] of Object.entries(formValues)) {
            formData.append(key, value);
        }

        // Post form and handle result
        post(this.el.getAttribute("action") + (this.el.dataset.force_action || this.el.dataset.model_name), formData)
            .then(async (resultData) => {
                // Restore send button behavior
                buttonEl.removeAttribute("disabled");
                buttonEl.classList.remove("disabled"); // !compatibility
                if (!resultData.id) {
                    // Failure, the server didn't return the created record ID
                    this.updateStatus("error", resultData.error ? resultData.error : false);
                    if (resultData.error_fields) {
                        // If the server return a list of bad fields, show these fields for users
                        this.checkErrorFields(resultData.error_fields);
                    }
                } else {
                    // Success, redirect or update status
                    let successMode = this.el.dataset.successMode;
                    let successPage = this.el.dataset.successPage;
                    if (!successMode) {
                        successPage = this.el.dataset.success_page; // !compatibility
                        successMode = successPage ? "redirect" : "nothing";
                    }
                    switch (successMode) {
                        case "redirect": {
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
                                if ([successPage, "/" + session.lang_url_code + successPage].some(link => link.startsWith(currentUrlPath + "#"))) {
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
                                        await this.waitFor(scrollTo(successAnchorEl, {
                                            duration: 500,
                                            extraOffset: 0,
                                        }));
                                    }
                                }
                                break;
                            }
                            window.location.href = successPage;
                            return;
                        }
                        case "message": {
                            // Prevent double-clicking on the send button and
                            // add a upload loading effect (delay before success
                            // message)
                            await delay(400);

                            this.isHidden = true;
                            break;
                        }
                        default: {
                            // Prevent double-clicking on the send button and
                            // add a upload loading effect (delay before success
                            // message)
                            await this.waitFor(delay(400));

                            this.updateStatus("success");
                            break;
                        }
                    }

                    this.resetForm();
                    this.restoreBtnLoading();
                }
            })
            .catch(error => {
                this.updateStatus(
                    "error",
                    error.status && error.status === 413 ? _t("Uploaded file is too large.") : "",
                );
            });
    }

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
    }

    checkErrorFields(errorFields) {
        let formValid = true;
        // Loop on all fields
        for (const fieldEl of this.el.querySelectorAll(".form-field, .s_website_form_field")) { // !compatibility
            // FIXME that seems broken, "for" does not contain the field
            // but this is used to retrieve errors sent from the server...
            // need more investigation.
            const fieldName = fieldEl.querySelector(".col-form-label")?.getAttribute("for");

            // Validate inputs for this field
            const inputEls = [...fieldEl.querySelectorAll(".s_website_form_input:not(#editable_select), .o_website_form_input:not(#editable_select)")]; // !compatibility
            const invalidInputs = inputEls.filter((inputEl) => {
                // Special check for multiple required checkbox for same
                // field as it seems checkValidity forces every required
                // checkbox to be checked, instead of looking at other
                // checkboxes with the same name and only requiring one
                // of them to be valid.
                if (inputEl.required && inputEl.type === "checkbox") {
                    // Considering we are currently processing a single
                    // field, we can assume that all checkboxes in the
                    // inputs variable have the same name
                    // TODO should be improved: probably do not need to
                    // filter neither on required, nor on checkbox and
                    // checking the validity of the group of checkbox is
                    // currently done for each checkbox of that group...
                    const checkboxes = inputEls.filter(el => el.required && el.type === "checkbox");
                    return !checkboxes.some((checkbox) => checkbox.checkValidity());

                    // Special cases for dates and datetimes
                    // FIXME this seems like dead code, the inputs do not use
                    // those classes, their parent does (but it seemed to work
                    // at some point given that https://github.com/odoo/odoo/commit/75e03c0f7692a112e1b0fa33267f4939363f3871
                    // was made)... need more investigation (if restored,
                    // consider checking the date inputs are not disabled before
                    // saying they are invalid (see checkValidity used here))
                } else if (inputEl.matches(".s_website_form_date, .o_website_form_date")) { // !compatibility
                    const date = parseDate(inputEl.value);
                    if (!date || !date.isValid) {
                        return true;
                    }
                } else if (inputEl.matches(".s_website_form_datetime, .o_website_form_datetime")) { // !compatibility
                    const date = parseDateTime(inputEl.value);
                    if (!date || !date.isValid) {
                        return true;
                    }
                } else if (inputEl.type === "file" && !this.isFileInputValid(inputEl)) {
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
                return !inputEl.checkValidity();
            });

            // Update field color if invalid or erroneous
            const controlEls = fieldEl.querySelectorAll(".form-control, .form-select, .form-check-input");
            fieldEl.classList.remove("o_has_error");
            for (const controlEl of controlEls) {
                controlEl.classList.remove("is-invalid");
            }
            if (invalidInputs.length || errorFields[fieldName]) {
                fieldEl.classList.add("o_has_error");
                for (const controlEl of controlEls) {
                    controlEl.classList.add("is-invalid");
                }
                if (typeof errorFields[fieldName] === "string") {
                    // update error message and show it.
                    const popover = Popover.getOrCreateInstance(fieldEl, {
                        content: errorFields[fieldName],
                        trigger: "hover",
                        container: "body",
                        placement: "top",
                    });
                    popover.show();
                }
                formValid = false;
            }
        }
        return formValid;
    }

    updateStatus(status, message) {
        if (status !== "success") { // Restore send button behavior if result is an error
            const buttonEl = this.el.querySelector(".s_website_form_send, .o_website_form_send");
            buttonEl.removeAttribute("disabled");
            buttonEl.classList.remove("disabled"); // !compatibility
            this.restoreBtnLoading();
        }
        const resultEl = this.el.querySelector("#s_website_form_result, #o_website_form_result"); // !compatibility

        if (status === "error" && !message) {
            message = _t("An error has occured, the form has not been sent.");
        }

        this.renderAt(`website.s_website_form_status_${status}`, {
            message: message,
        }, resultEl, "afterend");
        resultEl.remove();
    }

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
            this.fileInputError = { type: "number", limit: maxFilesNumber };
            return false;
        }
        // Checking the files size.
        const maxFileSize = inputEl.dataset.maxFileSize; // in megabytes.
        const bytesInMegabyte = 1_000_000;
        if (maxFileSize) {
            for (const file of Object.values(inputEl.files)) {
                if (file.size / bytesInMegabyte > maxFileSize) {
                    this.fileInputError = { type: "size", limit: maxFileSize, fileName: file.name };
                    return false;
                }
            }
        }
        return true;
    }

    /**
     * Gets the user's field needed to be fetched to pre-fill the form.
     *
     * @returns {string[]} List of user's field that have to be fetched.
     */
    getUserPreFillFields() {
        return ["name", "phone", "email", "commercial_company_name"];
    }

    /**
     * Compares the value with the comparable (and the between) with
     * comparator as a means to compare
     *
     * @param {string} comparator The way that $value and $comparable have
     *      to be compared
     * @param {string} [value] The value of the field
     * @param {string} [comparable] The value to compare
     * @param {string} [between] The maximum date value in case comparator
     *      is between or !between
     * @returns {boolean}
     */
    compareTo(comparator, value = "", comparable, between) {
        // Value can be null when the compared field is supposed to be
        // visible, but is not yet retrievable from the FormData() because
        // the field was conditionally hidden. It can be considered empty.
        if (value === null) {
            value = "";
        }

        switch (comparator) {
            case "contains":
                return value.includes(comparable);
            case "!contains":
                return !value.includes(comparable);
            case "equal":
            case "selected":
                return value === comparable;
            case "!equal":
            case "!selected":
                return value !== comparable;
            case "set":
                return value;
            case "!set":
                return !value;
            case "greater":
                return parseFloat(value) > parseFloat(comparable);
            case "less":
                return parseFloat(value) < parseFloat(comparable);
            case "greater or equal":
                return parseFloat(value) >= parseFloat(comparable);
            case "less or equal":
                return parseFloat(value) <= parseFloat(comparable);
            case "fileSet":
                return value.name !== "";
            case "!fileSet":
                return value.name === "";
        }

        const format = value.includes(":")
            ? localization.dateTimeFormat
            : localization.dateFormat;
        // Date & Date Time comparison requires formatting the value
        const dateTime = DateTime.fromFormat(value, format);
        // If invalid, any value other than "NaN" would cause certain
        // conditions to be broken.
        value = dateTime.isValid ? dateTime.toUnixInteger() : NaN;

        comparable = parseInt(comparable);
        between = parseInt(between) || "";
        switch (comparator) {
            case "dateEqual":
                return value === comparable;
            case "date!equal":
                return value !== comparable;
            case "before":
                return value < comparable;
            case "after":
                return value > comparable;
            case "equal or before":
                return value <= comparable;
            case "between":
                return value >= comparable && value <= between;
            case "!between":
                return !(value >= comparable && value <= between);
            case "equal or after":
                return value >= comparable;
        }
    }

    /**
     * @param {HTMLElement} fieldEl the field we want to have a function
     *      that calculates its visibility
     * @returns {function} the function to be executed when we want to
     *      recalculate the visibility of fieldEl
     */
    buildVisibilityFunction(fieldEl) {
        const visibilityCondition = fieldEl.dataset.visibilityCondition;
        const dependencyName = fieldEl.dataset.visibilityDependency;
        const comparator = fieldEl.dataset.visibilityComparator;
        const between = fieldEl.dataset.visibilityBetween;
        return () => {
            // To be visible, at least one field with the dependency name must be visible.
            const dependencyVisibilityFunction = this.visibilityFunctionByFieldName.get(dependencyName);
            const dependencyIsVisible = !dependencyVisibilityFunction || dependencyVisibilityFunction();
            if (!dependencyIsVisible) {
                return false;
            }

            const formData = new FormData(this.el);
            const currentValueOfDependency = ["contains", "!contains"].includes(comparator)
                ? formData.getAll(dependencyName).join()
                : formData.get(dependencyName);
            return this.compareTo(comparator, currentValueOfDependency, visibilityCondition, between);
        };
    }

    isFieldVisible(fieldEl) {
        const isVisible = this.visibilityFunctionByFieldEl.get(fieldEl);
        return isVisible ? !!isVisible() : true;
    }

    isInputVisible(inputEl) {
        return this.isFieldVisible(inputEl.closest(".s_website_form_field"));
    }

    /**
     * Creates a block containing the file name and a cross to delete it.
     *
     * @param {Object} fileDetails the details of the file being uploaded
     * @param {HTMLElement} filesZoneEl the zone where the file blocks are
     *      displayed
     */
    createFileBlock(fileDetails, filesZoneEl) {
        this.renderAt("website.file_block", { fileName: fileDetails.name }, filesZoneEl, "beforeend", (els) => els[0].fileDetails = fileDetails);
    }

    /**
     * Creates the file upload button (= a button to replace the file input,
     * in order to modify its text content more easily).
     *
     * @param {HTMLElement} inputEl the file input
     */
    createAddFilesButton(inputEl) {
        const addFilesButtonEl = document.createElement("INPUT");
        addFilesButtonEl.classList.add("o_add_files_button", "form-control");
        addFilesButtonEl.type = "button";
        addFilesButtonEl.value = inputEl.hasAttribute("multiple")
            ? _t("Add Files") : _t("Replace File");
        inputEl.parentNode.insertBefore(addFilesButtonEl, inputEl);
        inputEl.classList.add("d-none");
    }

    /**
     * Calculates the visibility of the fields at each input event on the
     * form (this method should be debounced in the start).
     */
    onFieldInput() {
        // Implicitly updates DOM.
    }

    /**
     * Called when files are uploaded: updates the button text content,
     * displays the file blocks (containing the files name and a cross to
     * delete them) and manages the files.
     *
     * @param {Event} ev
     */
    changeFile(ev) {
        const fileInputEl = ev.currentTarget;
        const fieldEl = fileInputEl.closest(".s_website_form_field");
        const uploadedFiles = fileInputEl.files;
        const addFilesButtonEl = fieldEl.querySelector(".o_add_files_button");

        // The zone where the file blocks are displayed.
        let filesZoneEl = fieldEl.querySelector(".o_files_zone");
        // Update the button text content.
        if (!addFilesButtonEl) {
            this.createAddFilesButton(fileInputEl);
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
                const fileDetails = { name: newFile.name, size: newFile.size, type: newFile.type };
                this.createFileBlock(fileDetails, filesZoneEl);
            }
        }
        // Update the input files.
        fileInputEl.files = fileInputEl.fileList.files;
    }

    /**
     * Called when a file is deleted by clicking on the cross on the block
     * describing it.
     *
     * @param {Event} ev
     */
    clickFileDelete(ev) {
        if (!ev.target.closest(".o_file_delete")) {
            return;
        }
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
        Object.assign(fileInputEl, { fileList: newFileList, files: newFileList.files });
        fileBlockEl.remove();

        // Restore the file input if there are no files uploaded and update
        // the fields visibility.
        if (!newFileList.files.length) {
            fileInputEl.classList.remove("d-none");
            addFilesButtonEl.remove();
        }
    }

    /**
     * Detects when the fake input file button is clicked to simulate a
     * click on the real input.
     *
     * @param {MouseEvent} ev
     */
    clickAddFilesButton(ev) {
        const fileInputEl = ev.target.parentNode.querySelector("input[type=file]");
        fileInputEl.click();
    }
}

registry
    .category("public.interactions")
    .add("website.form", Form);
