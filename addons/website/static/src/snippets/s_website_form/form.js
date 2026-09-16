/** @odoo-module native */
import { ReCaptcha } from "@google_recaptcha/js/recaptcha";
import { scrollTo } from "@html_builder/utils/scrolling";
import { makeLogger } from "@web/core/debug/debug_logger";
import {
    formatDate,
    formatDateTime,
    parseDate,
    parseDateTime,
    serializeDate,
    serializeDateTime,
} from "@web/core/l10n/dates";
import { localization } from "@web/core/l10n/localization";
import { luxon } from "@web/core/l10n/luxon";
import { post } from "@web/core/network";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/translation";
import { user } from "@web/core/user";
import { delay } from "@web/core/utils/concurrency";
import { Popover } from "@web/libs/bootstrap";
import { Interaction } from "@web/public/interaction";
import { session } from "@web/session";
import { getParsedDataFor } from "@website/js/utils";

const { DateTime } = luxon;

const log = makeLogger("website.form");

export class Form extends Interaction {
    static selector = ".s_website_form form, form.s_website_form";
    dynamicSelectors = {
        ...this.dynamicSelectors,
        _endMessage: () =>
            this.el.parentNode.querySelector(".s_website_form_end_message"),
    };
    sendLocked = this.locked(this.send, true);
    dynamicContent = {
        ".s_website_form_send, .o_website_form_send": {
            "t-on-click.prevent": this.sendLocked,
        },
        _root: {
            "t-on-submit.prevent": this.sendLocked,
            "t-att-class": () => ({
                "d-none": this.isHidden,
            }),
        },
        _endMessage: {
            "t-att-class": () => ({
                "d-none": !this.isHidden,
            }),
        },
        "input[type=file]": { "t-on-change": this.changeFile },
        "input.o_add_files_button": { "t-on-click": this.clickAddFilesButton },
        ".s_website_form_field[data-type=binary]": {
            "t-on-click": this.clickFileDelete,
        },
        ".s_website_form_field": {
            "t-on-input": this.debounced(this.onFieldInput, 300),
            "t-att-class": (el) => ({ "d-none": !this.isFieldVisible(el) }),
        },
        ".s_website_form_field:not(.s_website_form_model_required) .s_website_form_input":
            {
                "t-att-disabled": (el) => !this.isInputVisible(el) || undefined,
            },
        ".s_website_form_datetime, .o_website_form_datetime, .s_website_form_date, .o_website_form_date":
            {
                "t-att-class": () => ({
                    s_website_form_datepicker_initialized: this.datepickerInitialized,
                }),
            },
    };

    setup() {
        this.isHidden = false;
        this.datepickerInitialized = false;
        this.recaptcha = new ReCaptcha();
        this.initialValues = new Map();
        this.disabledStates = new Map();
        this.visibilityFunctionByFieldEl = new Map();
        this.visibilityFunctionByFieldName = new Map();
        this.inputEls = this.el.querySelectorAll(
            ".s_website_form_field.s_website_form_field_hidden_if .s_website_form_input",
        );
        this.dateFieldEls = this.el.querySelectorAll(
            ".s_website_form_datetime, .o_website_form_datetime, .s_website_form_date, .o_website_form_date",
        );
        this.disableDateTimePickers = [];
        this.preFillValues = {};
        this.lastFormData = this.getFormDataIncludingDisabledFields(this.el);
        log.lifecycle("setup", () => ({
            model: this.el.dataset.model_name,
            hiddenIfInputs: this.inputEls.length,
            dateFields: this.dateFieldEls.length,
        }));
    }

    async willStart() {
        log.logic("willStart", () => ({
            recaptcha: !this.el.classList.contains("s_website_form_no_recaptcha"),
            userPrefill: !!user.userId,
        }));
        if (!this.el.classList.contains("s_website_form_no_recaptcha")) {
            this.recaptchaLoaded = true;
            const endRecaptcha = log.perf("willStart recaptcha loadLibs");
            await this.recaptcha.loadLibs();
            endRecaptcha();
        }
        if (user.userId) {
            const fields = this.getUserPreFillFields();
            const readFields = fields.map((field) =>
                field === "phone" ? "phone_ids" : field,
            );
            const endReadUser = log.perf(
                "willStart read res.users prefill",
                readFields,
            );
            this.preFillValues =
                (
                    await this.services.orm.read("res.users", [user.userId], readFields)
                )[0] || {};
            endReadUser();
            if (fields.includes("phone")) {
                const [phoneId] = this.preFillValues.phone_ids || [];
                let phone;
                if (phoneId) {
                    const endReadPhone = log.perf("willStart read phone.number");
                    try {
                        [phone] = await this.services.orm.read(
                            "phone.number",
                            [phoneId],
                            ["number"],
                        );
                        endReadPhone();
                    } catch {
                        log.logic(
                            "willStart: phone.number read failed, no phone prefill",
                        );
                        phone = undefined;
                    }
                }
                this.preFillValues.phone = phone?.number || "";
            }
        }
        this.resetForm();

        const visibilityFunctionsByFieldName = new Map();
        for (const fieldEl of this.el.querySelectorAll(
            "[data-visibility-dependency]",
        )) {
            const inputName = fieldEl.querySelector(".s_website_form_input").name;
            if (!visibilityFunctionsByFieldName.has(inputName)) {
                visibilityFunctionsByFieldName.set(inputName, []);
            }
            const func = this.buildVisibilityFunction(fieldEl);
            visibilityFunctionsByFieldName.get(inputName).push(func);
            this.visibilityFunctionByFieldEl.set(fieldEl, func);
        }
        for (const [name, funcs] of visibilityFunctionsByFieldName.entries()) {
            this.visibilityFunctionByFieldName.set(name, () =>
                funcs.some((func) => func()),
            );
        }
        log.pipeline("willStart: visibility conditions built", () => ({
            conditionalFields: this.visibilityFunctionByFieldEl.size,
            dependencies: this.visibilityFunctionByFieldName.size,
        }));
    }

    start() {
        this.prepareDateFields();
        this.prefillValues();

        this.lastFormData = this.getFormDataIncludingDisabledFields(this.el);
        this.updateContent();

        if (session.geoip_phone_code) {
            log.logic("start: prefilling empty tel inputs with geoip code", () => ({
                code: session.geoip_phone_code,
                telInputs: this.el.querySelectorAll(`input[type="tel"]`).length,
            }));
            this.el.querySelectorAll(`input[type="tel"]`).forEach((telField) => {
                if (!telField.value) {
                    telField.value = "+" + session.geoip_phone_code;
                }
            });
        }
        for (const inputEl of this.inputEls) {
            this.disabledStates.set(inputEl, inputEl.disabled);
        }

        this.el.querySelectorAll("input[type=file]").forEach((inputEl) => {
            const filesZoneEl = document.createElement("DIV");
            filesZoneEl.classList.add("o_files_zone", "row", "gx-1");
            inputEl.parentNode.insertBefore(filesZoneEl, inputEl);
        });
        log.lifecycle("start", () => ({
            datepickers: this.disableDateTimePickers.length,
            fileInputs: this.el.querySelectorAll("input[type=file]").length,
        }));
    }

    destroy() {
        log.lifecycle("destroy", () => ({
            errors: this.el.querySelectorAll(".o_has_error").length,
            initialValues: this.initialValues.size,
            datepickers: this.disableDateTimePickers.length,
        }));
        this.resetForm();

        this.el
            .querySelectorAll(
                `input[type="text"], input[type="email"], input[type="number"]`,
            )
            .forEach((el) => {
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
        this.el
            .querySelectorAll("textarea")
            .forEach((el) => (el.value = el.textContent));

        for (const errorEl of this.el.querySelectorAll(".o_has_error")) {
            errorEl.classList.remove("o_has_error");
            for (const el of errorEl.querySelectorAll(".form-control, .form-select")) {
                el.classList.remove("is-invalid");
            }
            Popover.getInstance(errorEl)?.dispose();
        }

        this.el
            .querySelector("#s_website_form_result, #o_website_form_result")
            ?.replaceChildren();

        for (const inputEl of this.inputEls) {
            inputEl.disabled = !!this.disabledStates.get(inputEl);
        }

        this.el
            .querySelectorAll(".s_website_form_field_hidden_if:not(.d-none)")
            .forEach((el) => el.classList.add("d-none"));

        const dataForValues = getParsedDataFor(this.el.id, document) || {};
        const initialValuesToReset = new Map(
            [...this.initialValues.entries()].filter(
                ([input]) => !dataForValues[input.name] || input.name === "email_to",
            ),
        );

        for (const [fieldEl, initialValue] of initialValuesToReset.entries()) {
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
            const picker = this.services.datetime_picker.create({
                target: inputEl,
                onChange: () =>
                    inputEl.dispatchEvent(new Event("input", { bubbles: true })),
                pickerProps: {
                    type: fieldEl.matches(".s_website_form_date, .o_website_form_date")
                        ? "date"
                        : "datetime",
                    value: defaultValue
                        ? DateTime.fromSeconds(parseInt(defaultValue))
                        : false,
                },
            });
            picker.enable();
            this.disableDateTimePickers.push(() => picker.dispose());
            inputEl.setAttribute("inputmode", "none");
        }
        log.pipeline("prepareDateFields: datepickers enabled", () => ({
            count: this.dateFieldEls.length,
        }));
        this.datepickerInitialized = true;
    }

    prefillValues() {
        let dataForValues = getParsedDataFor(this.el.id, document);
        log.logic("prefillValues", () => ({
            hasDataFor: !!dataForValues,
            userPrefill: Object.keys(this.preFillValues),
        }));
        if (dataForValues || Object.keys(this.preFillValues).length) {
            dataForValues = dataForValues || {};
            const fieldNames = [...this.el.querySelectorAll("[name]")]
                .filter(
                    (el) =>
                        !["submit", "button", "image", "reset", "file"].includes(
                            el.type,
                        ),
                )
                .map((el) => el.name);

            for (const name of fieldNames) {
                const fieldEl = this.el.querySelector(`[name="${CSS.escape(name)}"]`);

                if (
                    name === "email_to" &&
                    fieldEl.value &&
                    fieldEl.value !== "info@yourcompany.example.com"
                ) {
                    log.logic("prefillValues: keeping custom email_to");
                    continue;
                }

                let newValue;
                if (dataForValues && dataForValues[name]) {
                    newValue = dataForValues[name];
                } else if (this.preFillValues[fieldEl.dataset.fillWith]) {
                    newValue = this.preFillValues[fieldEl.dataset.fillWith];
                }
                if (newValue) {
                    log.logic("prefillValues: field prefilled", () => ({
                        name,
                        fromDataFor: !!dataForValues[name],
                    }));
                    this.initialValues.set(fieldEl, fieldEl.getAttribute("value"));
                    fieldEl.value = newValue;
                }
            }
        }
    }

    async send() {
        log.logic("send", () => ({
            action: this.el.dataset.model_name,
            fields: this.el.querySelectorAll(".s_website_form_field").length,
        }));
        this.el
            .querySelector("#s_website_form_result, #o_website_form_result")
            ?.replaceChildren();
        this.removeErrorMessages();
        if (!this.checkErrorFields({})) {
            log.logic("send: client-side validation failed", () => ({
                invalidFields: this.el.querySelectorAll(".o_has_error").length,
            }));
            this.updateStatus("error", _t("Please fill in the form correctly."));
            return false;
        }

        for (const [i, inputEl] of this.el
            .querySelectorAll(".s_website_form_input:is(:not([name]), [name=''])")
            .entries()) {
            inputEl.setAttribute("name", "unknown_field_" + (i + 1));
        }

        const formFields = [];
        new FormData(this.el).forEach((value, key) => {
            const inputElement = this.el.querySelector(`[name="${CSS.escape(key)}"]`);
            if (inputElement && inputElement.type !== "file") {
                formFields.push({ name: key, value: value });
            }
        });
        let outerIndex = 0;
        for (const inputEl of this.el.querySelectorAll(
            "input[type=file]:not([disabled])",
        )) {
            let index = 0;
            for (const file of inputEl.files) {
                formFields.push({
                    name: `${inputEl.name}[${outerIndex}][${index}]`,
                    value: file,
                });
                index++;
            }
            outerIndex++;
        }
        log.pipeline("send: collected form fields", () => ({
            fields: formFields.length,
            files: formFields.filter((input) => input.value instanceof File).length,
            fileInputs: outerIndex,
        }));

        const formValues = {};
        formFields.forEach((input) => {
            if (input.name in formValues) {
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

        for (const fieldEl of this.el.querySelectorAll(
            ".s_website_form_field:not(.s_website_form_custom)",
        )) {
            for (const dateEl of fieldEl.querySelectorAll(
                ".s_website_form_date, .s_website_form_datetime",
            )) {
                const inputEl = dateEl.querySelector("input");
                const { value } = inputEl;
                if (!value) {
                    continue;
                }

                formValues[inputEl.getAttribute("name")] = dateEl.matches(
                    ".s_website_form_date",
                )
                    ? serializeDate(parseDate(value))
                    : serializeDateTime(parseDateTime(value));
            }
        }

        if (this.recaptchaLoaded) {
            const endToken = log.perf("send recaptcha getToken");
            const tokenObj = await this.waitFor(
                this.recaptcha.getToken("website_form"),
            );
            endToken(() => ({ token: !!tokenObj.token, error: !!tokenObj.error }));
            if (tokenObj.token) {
                formValues["recaptcha_token_response"] = tokenObj.token;
            } else if (tokenObj.error) {
                log.logic("send: recaptcha token error, aborting", () => ({
                    error: tokenObj.error,
                }));
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
        log.pipeline("send: posting form", () => ({
            action: this.el.getAttribute("action"),
            model: this.el.dataset.force_action || this.el.dataset.model_name,
            values: Object.keys(formValues).length,
        }));

        const endPost = log.perf("send post");
        return post(
            this.el.getAttribute("action") +
                (this.el.dataset.force_action || this.el.dataset.model_name),
            formData,
        )
            .then(async (resultData) => {
                endPost(() => ({ id: resultData.id, error: !!resultData.error }));
                if (!resultData.id) {
                    log.logic("send: server rejected submission", () => ({
                        error: resultData.error,
                        errorFields: Object.keys(resultData.error_fields || {}),
                    }));
                    this.updateStatus(
                        "error",
                        resultData.error ? resultData.error : false,
                    );
                    if (resultData.error_fields) {
                        this.checkErrorFields(resultData.error_fields);
                    }
                } else {
                    let successMode = this.el.dataset.successMode;
                    let successPage = this.el.dataset.successPage;
                    if (!successMode) {
                        successPage = this.el.dataset.success_page;
                        successMode = successPage ? "redirect" : "nothing";
                    }
                    log.logic("send: success", () => ({
                        successMode,
                        successPage,
                        legacy: !this.el.dataset.successMode,
                    }));
                    switch (successMode) {
                        case "redirect": {
                            let hashIndex = successPage.indexOf("#");
                            if (hashIndex > 0) {
                                let currentUrlPath = window.location.pathname;
                                if (!currentUrlPath.endsWith("/")) {
                                    currentUrlPath = currentUrlPath + "/";
                                }
                                if (!successPage.includes("/#")) {
                                    successPage = successPage.replace("#", "/#");
                                    hashIndex++;
                                }
                                if (
                                    [
                                        successPage,
                                        "/" + session.lang_url_code + successPage,
                                    ].some((link) =>
                                        link.startsWith(currentUrlPath + "#"),
                                    )
                                ) {
                                    successPage = successPage.substring(hashIndex);
                                }
                            }
                            if (successPage.charAt(0) === "#") {
                                const successAnchorEl = document.getElementById(
                                    successPage.substring(1),
                                );
                                if (successAnchorEl) {
                                    log.logic("send: success anchor on page", () => ({
                                        anchor: successPage,
                                        modal: successAnchorEl.classList.contains(
                                            "modal",
                                        ),
                                    }));
                                    if (successAnchorEl.classList.contains("modal")) {
                                        window.location.href = successPage;
                                    } else {
                                        await this.waitFor(
                                            scrollTo(successAnchorEl, {
                                                duration: 500,
                                                extraOffset: 0,
                                            }),
                                        );
                                    }
                                }
                                break;
                            }
                            log.logic("send: redirecting to success page", () => ({
                                successPage,
                            }));
                            window.location.href = successPage;
                            return;
                        }
                        case "message": {
                            await this.waitFor(delay(400));

                            this.isHidden = true;
                            break;
                        }
                        default: {
                            await this.waitFor(delay(400));

                            this.updateStatus("success");
                            break;
                        }
                    }

                    this.resetForm();
                }
            })
            .catch((error) => {
                endPost(() => ({ failed: true }));
                log.logic("send: post failed", () => ({
                    message: error.message,
                    tooLarge: error.message === "Content too large",
                }));
                this.updateStatus(
                    "error",
                    error.message && error.message === "Content too large"
                        ? _t("Uploaded file is too large.")
                        : "",
                );
            });
    }

    resetForm() {
        this.el.reset();

        this.removeErrorMessages();
        this.el.querySelectorAll("input[type=file]").forEach((inputEl) => {
            const fieldEl = inputEl.closest(".s_website_form_field");
            fieldEl.querySelectorAll(".o_files_zone").forEach((el) => el.remove());
            fieldEl
                .querySelectorAll(".o_add_files_button")
                .forEach((el) => el.remove());
            inputEl.classList.remove("d-none");
            delete inputEl.fileList;
        });
    }

    checkErrorFields(errorFields) {
        let formValid = true;
        for (const fieldEl of this.el.querySelectorAll(
            ".form-field, .s_website_form_field",
        )) {
            const fieldName = fieldEl
                .querySelector(".col-form-label")
                ?.getAttribute("for");

            const inputEls = [
                ...fieldEl.querySelectorAll(
                    ".s_website_form_input:not(#editable_select), .o_website_form_input:not(#editable_select)",
                ),
            ];
            const invalidInputs = inputEls.filter((inputEl) => {
                if (inputEl.required && inputEl.type === "checkbox") {
                    const checkboxes = inputEls.filter(
                        (el) => el.required && el.type === "checkbox",
                    );
                    return !checkboxes.some((checkbox) => checkbox.checkValidity());
                } else if (
                    inputEl.matches(".s_website_form_date, .o_website_form_date")
                ) {
                    const date = parseDate(inputEl.value);
                    if (!date || !date.isValid) {
                        log.logic("checkErrorFields: invalid date", () => ({
                            name: inputEl.name,
                        }));
                        return true;
                    }
                } else if (
                    inputEl.matches(
                        ".s_website_form_datetime, .o_website_form_datetime",
                    )
                ) {
                    const date = parseDateTime(inputEl.value);
                    if (!date || !date.isValid) {
                        log.logic("checkErrorFields: invalid datetime", () => ({
                            name: inputEl.name,
                        }));
                        return true;
                    }
                } else if (inputEl.type === "file" && !this.isFileInputValid(inputEl)) {
                    log.logic("checkErrorFields: invalid file input", () => ({
                        name: inputEl.name,
                    }));
                    return true;
                } else if (this.requirementFunction(fieldEl) === false) {
                    log.logic("checkErrorFields: requirement condition failed", () => ({
                        name: inputEl.name,
                        comparator: fieldEl.dataset.requirementComparator,
                    }));
                    this.updateStatusInline(fieldEl.dataset.errorMessage, inputEl);
                    return true;
                }

                return !inputEl.checkValidity();
            });

            const controlEls = fieldEl.querySelectorAll(
                ".form-control, .form-select, .form-check-input",
            );
            fieldEl.classList.remove("o_has_error");
            for (const controlEl of controlEls) {
                controlEl.classList.remove("is-invalid");
            }
            Popover.getInstance(fieldEl)?.dispose();
            if (invalidInputs.length || errorFields[fieldName]) {
                log.logic("checkErrorFields: field marked invalid", () => ({
                    fieldName,
                    invalidInputs: invalidInputs.length,
                    serverError: typeof errorFields[fieldName],
                }));
                fieldEl.classList.add("o_has_error");
                for (const controlEl of controlEls) {
                    controlEl.classList.add("is-invalid");
                }
                if (typeof errorFields[fieldName] === "string") {
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
        log.logic("checkErrorFields: result", () => ({
            formValid,
            serverErrorFields: Object.keys(errorFields).length,
        }));
        return formValid;
    }

    updateStatus(status, message) {
        const resultEl = this.el.querySelector(
            "#s_website_form_result, #o_website_form_result",
        );

        log.logic("updateStatus", () => ({
            status,
            hasMessage: !!message,
            hasResultEl: !!resultEl,
        }));
        if (status === "error" && !message) {
            message = _t("An error has occured, the form has not been sent.");
        }

        const renderedEls = this.renderAt(
            `website.s_website_form_status_${status}`,
            {
                message: message,
            },
            resultEl,
            "afterend",
            undefined,
            false,
        );
        this.registerCleanup(() => {
            for (const el of renderedEls) {
                const renderedResultEl = el.matches("#s_website_form_result")
                    ? el
                    : el.querySelector("#s_website_form_result");
                renderedResultEl.replaceChildren();
            }
        });
        resultEl.remove();
    }
    /**
     * @param {string} message
     * @param {HTMLElement} inputEl
     */
    updateStatusInline(message, inputEl) {
        if (inputEl.parentElement.classList.contains("date")) {
            this.renderAt(
                "website.s_website_form_status_custom_error",
                {
                    message,
                },
                inputEl.parentElement,
                "afterend",
            );
        } else {
            this.renderAt(
                "website.s_website_form_status_custom_error",
                {
                    message,
                },
                inputEl.parentElement,
                "beforeend",
            );
        }
    }

    /**
     * @param {HTMLElement} inputEl
     * @returns {Boolean}
     */
    isFileInputValid(inputEl) {
        const maxFilesNumber = inputEl.dataset.maxFilesNumber;
        if (maxFilesNumber && inputEl.files.length > maxFilesNumber) {
            log.logic("isFileInputValid: too many files", () => ({
                files: inputEl.files.length,
                maxFilesNumber,
            }));
            const errorMessage = _t(
                "You have uploaded too many files(Maximum %s files).",
                maxFilesNumber,
            );
            this.updateStatusInline(errorMessage, inputEl);
            return false;
        }
        const maxFileSize = inputEl.dataset.maxFileSize;
        const bytesInMegabyte = 1_000_000;
        if (maxFileSize) {
            for (const file of Object.values(inputEl.files)) {
                if (file.size / bytesInMegabyte > maxFileSize) {
                    log.logic("isFileInputValid: file too large", () => ({
                        size: file.size,
                        maxFileSize,
                    }));
                    const errorMessage = _t(
                        "Please fill in the form correctly. The file “%(fileName)s” is too large. (Maximum %(max)s MB)",
                        { fileName: file.name, max: maxFileSize },
                    );
                    this.updateStatusInline(errorMessage, inputEl);
                    return false;
                }
            }
        }
        return true;
    }

    /**
     * @returns {string[]}
     */
    getUserPreFillFields() {
        return ["name", "phone", "email", "commercial_company_name"];
    }

    /**
     * @param {string} comparator
     * @param {string} [value]
     * @param {string} [comparable]
     * @param {string} [between]
     * @returns {boolean}
     */
    compareTo(comparator, value = "", comparable, between) {
        if (value === null) {
            value = "";
        }

        switch (comparator) {
            case "contains":
                return value.includes(comparable);
            case "!contains":
                return !value.includes(comparable);
            case "substring":
                return value.includes(comparable);
            case "!substring":
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

        let format;
        const xYearAgo = new Date();
        if (value.includes(":")) {
            format = localization.dateTimeFormat;
        } else {
            format = localization.dateFormat;
            xYearAgo.setHours(0, 0, 0, 0);
        }
        const dateTime = DateTime.fromFormat(value, format);
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
            case "lessyears":
                xYearAgo.setFullYear(new Date().getFullYear() - comparable);
                value = new Date(value * 1000);
                return value > xYearAgo;
        }
    }

    /**
     * @param {HTMLElement} fieldEl
     * @returns {function}
     */
    buildVisibilityFunction(fieldEl) {
        const visibilityCondition = fieldEl.dataset.visibilityCondition;
        const dependencyName = fieldEl.dataset.visibilityDependency;
        const comparator = fieldEl.dataset.visibilityComparator;
        const between = fieldEl.dataset.visibilityBetween;
        return () => {
            const dependencyVisibilityFunction =
                this.visibilityFunctionByFieldName.get(dependencyName);
            const dependencyIsVisible =
                !dependencyVisibilityFunction || dependencyVisibilityFunction();
            if (!dependencyIsVisible) {
                return false;
            }

            const currentValueOfDependency = ["contains", "!contains"].includes(
                comparator,
            )
                ? this.lastFormData.getAll(dependencyName).join()
                : this.lastFormData.get(dependencyName);
            return this.compareTo(
                comparator,
                currentValueOfDependency,
                visibilityCondition,
                between,
            );
        };
    }

    /**
     * @param {HTMLElement} formEl
     * @returns {FormData}
     */
    getFormDataIncludingDisabledFields(formEl) {
        const disabledFields = formEl.querySelectorAll(
            "input:disabled, select:disabled, textarea:disabled",
        );
        disabledFields.forEach((element) => {
            element.removeAttribute("disabled");
        });
        const formData = new FormData(formEl);
        disabledFields.forEach((element) => {
            element.setAttribute("disabled", true);
        });
        return formData;
    }

    /**
     * @private
     * @param {HTMLElement} fieldEl
     * @returns {boolean}
     */
    requirementFunction(fieldEl) {
        const {
            requirementCondition: condition,
            requirementComparator: comparator,
            requirementBetween: between,
        } = fieldEl.dataset;
        const value = fieldEl.querySelector(".s_website_form_input").value;
        if (!condition && comparator) {
            return true;
        }
        if (["between", "!between"].includes(comparator) && !between) {
            return true;
        }
        if (!value.trim()) {
            return true;
        }
        return this.compareTo(comparator, value, condition, between);
    }

    isFieldVisible(fieldEl) {
        const isVisible = this.visibilityFunctionByFieldEl.get(fieldEl);
        return isVisible ? !!isVisible() : true;
    }

    isInputVisible(inputEl) {
        return this.isFieldVisible(inputEl.closest(".s_website_form_field"));
    }

    /**
     * @param {Object} fileDetails
     * @param {HTMLElement} filesZoneEl
     */
    createFileBlock(fileDetails, filesZoneEl) {
        this.renderAt(
            "website.file_block",
            { fileName: fileDetails.name },
            filesZoneEl,
            "beforeend",
            (els) => (els[0].fileDetails = fileDetails),
        );
    }

    /**
     * @param {HTMLElement} inputEl
     */
    createAddFilesButton(inputEl) {
        const addFilesButtonEl = document.createElement("INPUT");
        addFilesButtonEl.classList.add("o_add_files_button", "form-control");
        addFilesButtonEl.type = "button";
        addFilesButtonEl.value = inputEl.hasAttribute("multiple")
            ? _t("Add Files")
            : _t("Replace File");
        inputEl.parentNode.insertBefore(addFilesButtonEl, inputEl);
        inputEl.classList.add("d-none");
    }

    onFieldInput() {
        this.lastFormData = this.getFormDataIncludingDisabledFields(this.el);
        log.logic("onFieldInput: form data refreshed", () => ({
            conditionalFields: this.visibilityFunctionByFieldEl.size,
        }));
    }

    /**
     * @param {Event} ev
     */
    changeFile(ev) {
        const fileInputEl = ev.currentTarget;
        const fieldEl = fileInputEl.closest(".s_website_form_field");
        const uploadedFiles = fileInputEl.files;
        const addFilesButtonEl = fieldEl.querySelector(".o_add_files_button");

        const filesZoneEl = fieldEl.querySelector(".o_files_zone");
        if (!addFilesButtonEl) {
            this.createAddFilesButton(fileInputEl);
        }

        if (!fileInputEl.fileList) {
            fileInputEl.fileList = new DataTransfer();
        }

        if (!fileInputEl.hasAttribute("multiple") && uploadedFiles.length > 0) {
            log.logic("changeFile: single-file input, replacing previous file");
            fileInputEl.fileList = new DataTransfer();
            const fileBlockEl = fieldEl.querySelector(".o_file_block");
            if (fileBlockEl) {
                fileBlockEl.remove();
            }
        }

        for (const newFile of uploadedFiles) {
            if (
                ![...fileInputEl.fileList.files].some(
                    (file) =>
                        newFile.name === file.name &&
                        newFile.size === file.size &&
                        newFile.type === file.type,
                )
            ) {
                fileInputEl.fileList.items.add(newFile);
                const fileDetails = {
                    name: newFile.name,
                    size: newFile.size,
                    type: newFile.type,
                };
                this.createFileBlock(fileDetails, filesZoneEl);
            }
        }
        fileInputEl.files = fileInputEl.fileList.files;
        log.pipeline("changeFile: file list updated", () => ({
            name: fileInputEl.name,
            uploaded: uploadedFiles.length,
            total: fileInputEl.files.length,
        }));
    }

    /**
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

        const newFileList = new DataTransfer();
        for (const file of Object.values(fileInputEl.fileList.files)) {
            if (
                file.name !== fileDetails.name ||
                file.size !== fileDetails.size ||
                file.type !== fileDetails.type
            ) {
                newFileList.items.add(file);
            }
        }
        Object.assign(fileInputEl, { fileList: newFileList, files: newFileList.files });
        fileBlockEl.remove();
        log.pipeline("clickFileDelete: file removed", () => ({
            name: fileInputEl.name,
            remaining: newFileList.files.length,
        }));

        if (!newFileList.files.length) {
            fileInputEl.classList.remove("d-none");
            addFilesButtonEl.remove();
        }
    }

    /**
     * @param {MouseEvent} ev
     */
    clickAddFilesButton(ev) {
        const fileInputEl = ev.target.parentNode.querySelector("input[type=file]");
        fileInputEl.click();
    }
    removeErrorMessages() {
        this.el.querySelectorAll(".s_website_form_custom_error").forEach((error) => {
            error.remove();
        });
    }
}

registry.category("public.interactions").add("website.form", Form);
