import { registry } from "@web/core/registry";
import { Cache } from "@web/core/utils/cache";
import { Plugin } from "@html_editor/plugin";
import { FormOption } from "./form_option";
import { FormOptionAddFieldButton } from "./form_option_add_field_button";
import {
    getCustomField,
    getDefaultFormat,
    getFieldFormat,
    getMark,
    isOptionalMark,
    isRequiredMark,
    renderField,
} from "./utils";
import { SyncCache } from "@html_builder/utils/sync_cache";
import { _t } from "@web/core/l10n/translation";
import { renderToElement } from "@web/core/utils/render";

export class FormOptionPlugin extends Plugin {
    static id = "websiteFormOption";
    static dependencies = ["builderActions", "builder-options"];
    resources = {
        builder_header_middle_buttons: [
            {
                Component: FormOptionAddFieldButton,
                selector: ".s_website_form",
                applyTo: "form",
                props: {
                    addField: (formEl) => this.addFieldToForm(formEl),
                    tooltip: _t("Add a new field at the end"),
                },
            },
            {
                Component: FormOptionAddFieldButton,
                selector: ".s_website_form_field",
                exclude: ".s_website_form_dnone",
                props: {
                    addField: (fieldEl) => this.addFieldAfterField(fieldEl),
                    tooltip: _t("Add a new field after this one"),
                },
            },
        ],
        builder_options: [
            {
                OptionComponent: FormOption,
                props: {
                    fetchModels: this.fetchModels.bind(this),
                    prepareFormModel: this.prepareFormModel.bind(this),
                    fetchFieldRecords: this.fetchFieldRecords.bind(this),
                    applyFormModel: this.applyFormModel.bind(this),
                },
                selector: ".s_website_form",
                applyTo: "form",
            },
        ],
        builder_actions: this.getActions(),
        system_classes: ["o_builder_form_show_message"],
        normalize_handlers: (el) => {
            for (const formEl of el.querySelectorAll(".s_website_form form")) {
                // Disable text edition
                formEl.contentEditable = "false";
                // Identify editable elements of the form: buttons, description,
                // recaptcha and columns which are not fields.
                const formEditableSelector = [
                    ".s_website_form_send",
                    ".s_website_form_field_description",
                    ".s_website_form_recaptcha",
                    ".row > div:not(.s_website_form_field, .s_website_form_submit, .s_website_form_field *, .s_website_form_submit *)",
                ]
                    .map((selector) => `:scope ${selector}`)
                    .join(", ");
                for (const formEditableEl of formEl.querySelectorAll(formEditableSelector)) {
                    formEditableEl.contentEditable = "true";
                }
            }
        },
        clean_for_save_handlers: ({ root: el }) => {
            // Maybe useless if all contenteditable are removed
            for (const formEl of el.querySelectorAll(".s_website_form form")) {
                formEl.removeAttribute("contenteditable");
            }
        },
    };
    getActions() {
        return {
            // Components that use this action MUST await fetchModels before they start.
            selectAction: {
                load: async ({ editingElement: el, value: modelId }) => {
                    const modelCantChange = !!el.getAttribute("hide-change-model");
                    if (modelCantChange) {
                        return;
                    }
                    const activeForm = this.modelsCache
                        .get()
                        .find((model) => model.id === parseInt(modelId));
                    return { activeForm, formInfo: await this.prepareFormModel(el, activeForm) };
                },
                apply: ({ editingElement: el, value: modelId, loadResult }) => {
                    if (!loadResult) {
                        return;
                    }
                    this.applyFormModel(
                        el,
                        loadResult.activeForm,
                        parseInt(modelId),
                        loadResult.formInfo
                    );
                },
                isApplied: ({ editingElement: el, value: modelId }) => {
                    const models = this.modelsCache.get();
                    const targetModelName = el.dataset.model_name || "mail.mail";
                    const activeForm = models.find((m) => m.model === targetModelName);
                    return parseInt(modelId) === activeForm.id;
                },
            },
            // Select the value of a field (hidden) that will be used on the model as a preset.
            // ie: The Job you apply for if the form is on that job's page.
            addActionField: {
                load: async ({ editingElement: el }) => this.fetchAuthorizedFields(el),
                apply: ({ editingElement: el, value, param, loadResult: authorizedFields }) => {
                    // Remove old property fields.
                    for (const [fieldName, field] of Object.entries(authorizedFields)) {
                        if (field._property) {
                            for (const inputEl of el.querySelectorAll(`[name="${fieldName}"]`)) {
                                inputEl.closest(".s_website_form_field").remove();
                            }
                        }
                    }
                    const fieldName = param.fieldName;
                    if (param.isSelect === "true") {
                        value = parseInt(value);
                    }
                    this.addHiddenField(el, value, fieldName);
                },
                // TODO clear ? if field is a boolean ?
                getValue: ({ editingElement: el, param }) => {
                    // TODO Convert
                    const value = el.querySelector(
                        `.s_website_form_dnone input[name="${param.fieldName}"]`
                    )?.value;
                    if (param.fieldName === "email_to") {
                        // For email_to, we try to find a value in this order:
                        // 1. The current value of the input
                        // 2. The data-for value if it exists
                        // 3. The default value (`defaultEmailToValue`)
                        if (value && value !== this.defaultEmailToValue) {
                            return value;
                        }
                        return this.dataForEmailTo || this.defaultEmailToValue;
                    }
                    if (value) {
                        return value;
                    } else {
                        return param.isSelect ? "0" : "";
                    }
                },
                isApplied: ({ editingElement, param, value }) => {
                    const getAction = this.dependencies.builderActions.getAction;
                    const currentValue = getAction("addActionField").getValue({
                        editingElement,
                        param,
                    });
                    return currentValue === value;
                },
            },
            promptSaveRedirect: {
                apply: ({ editingElement: el }) => {
                    // TODO Convert after reload-related operations are available
                    /*
                    return new Promise((resolve, reject) => {
                        const message = _t("Would you like to save before being redirected? Unsaved changes will be discarded.");
                        this.dialog.add(ConfirmationDialog, {
                            body: message,
                            confirmLabel: _t("Save"),
                            confirm: () => {
                                this.env.requestSave({
                                    reload: false,
                                    onSuccess: () => {
                                        this._redirectToAction(value);
                                    },
                                    onFailure: () => {
                                        this.notification.add(_t("Something went wrong."), {
                                            type: 'danger',
                                            sticky: true,
                                        });
                                    },
                                });
                                resolve();
                            },
                            cancel: () => resolve(),
                        });
                    });
                    */
                },
            },
            updateLabelsMark: {
                apply: ({ editingElement: el }) => {
                    this.setLabelsMark(el);
                },
                isApplied: () => true,
            },
            setMark: {
                apply: ({ editingElement: el, value }) => {
                    el.dataset.mark = value.trim();
                    this.setLabelsMark(el);
                },
                getValue: ({ editingElement: el }) => {
                    const mark = getMark(el);
                    return mark;
                },
            },
            onSuccess: {
                apply: ({ editingElement: el, value }) => {
                    el.dataset.successMode = value;
                    let messageEl = el.parentElement.querySelector(".s_website_form_end_message");
                    if (value === "message") {
                        if (!messageEl) {
                            messageEl = renderToElement("website.s_website_form_end_message");
                            el.insertAdjacentElement("afterend", messageEl);
                        }
                    } else {
                        messageEl?.remove();
                        messageEl?.classList.remove("o_builder_form_show_message");
                        el.classList.remove("o_builder_form_show_message");
                    }
                },
                isApplied: ({ editingElement: el, value }) => {
                    const currentValue = el.dataset.successMode;
                    return currentValue === value;
                },
            },
            toggleEndMessage: {
                apply: ({ editingElement: el }) => {
                    const messageEl = el.parentElement.querySelector(".s_website_form_end_message");
                    messageEl.classList.add("o_builder_form_show_message");
                    el.classList.add("o_builder_form_show_message");
                    this.dependencies["builder-options"].updateContainers(messageEl);
                },
                clean: ({ editingElement: el }) => {
                    const messageEl = el.parentElement.querySelector(".s_website_form_end_message");
                    messageEl.classList.remove("o_builder_form_show_message");
                    el.classList.remove("o_builder_form_show_message");
                    this.dependencies["builder-options"].updateContainers(el);
                },
                isApplied: ({ editingElement: el, value }) =>
                    el.classList.contains("o_builder_form_show_message"),
            },
            formToggleRecaptchaLegal: {
                apply: ({ editingElement: el }) => {
                    const labelWidth = el.querySelector(".s_website_form_label").style.width;
                    const legalEl = renderToElement("website.s_website_form_recaptcha_legal", {
                        labelWidth: labelWidth,
                    });
                    legalEl.setAttribute("contentEditable", true);
                    el.querySelector(".s_website_form_submit").insertAdjacentElement(
                        "beforebegin",
                        legalEl
                    );
                },
                clean: ({ editingElement: el }) => {
                    const recaptchaLegalEl = el.querySelector(".s_website_form_recaptcha");
                    recaptchaLegalEl.remove();
                },
                isApplied: ({ editingElement: el }) => {
                    const recaptchaLegalEl = el.querySelector(".s_website_form_recaptcha");
                    return !!recaptchaLegalEl;
                },
            },
        };
    }
    setup() {
        this.modelsCache = new SyncCache(this._fetchModels.bind(this));
        this.fieldRecordsCache = new SyncCache(this._fetchFieldRecords.bind(this));
        this.authorizedFieldsCache = new Cache(
            this._fetchAuthorizedFields.bind(this),
            ({ cacheKey }) => cacheKey
        );
    }
    destroy() {
        super.destroy();
        this.modelsCache.invalidate();
        this.fieldRecordsCache.invalidate();
        this.authorizedFieldsCache.invalidate();
    }
    async fetchModels() {
        return this.modelsCache.preload();
    }
    async _fetchModels() {
        return await this.services.orm.call("ir.model", "get_compatible_form_models");
    }
    async fetchFieldRecords(field) {
        return this.fieldRecordsCache.preload(field);
    }
    /**
     * Returns a promise which is resolved once the records of the field
     * have been retrieved.
     *
     * @param {Object} field
     * @returns {Promise<Object>}
     */
    async _fetchFieldRecords(field) {
        // Convert the required boolean to a value directly usable
        // in qweb js to avoid duplicating this in the templates
        field.required = field.required ? 1 : null;

        if (field.records) {
            return field.records;
        }
        if (field._property && field.type === "tags") {
            // Convert tags to records to avoid added complexity.
            // Tag ids need to escape "," to be able to recover their value on
            // the server side if they contain ",".
            field.records = field.tags.map((tag) => ({
                id: tag[0].replaceAll("\\", "\\/").replaceAll(",", "\\,"),
                display_name: tag[1],
            }));
        } else if (field._property && field.comodel) {
            field.records = await this.services.orm.searchRead(field.comodel, field.domain || [], [
                "display_name",
            ]);
        } else if (field.type === "selection") {
            // Set selection as records to avoid added complexity.
            field.records = field.selection.map((el) => ({
                id: el[0],
                display_name: el[1],
            }));
        } else if (field.relation && field.relation !== "ir.attachment") {
            const fieldNames = field.fieldName ? [field.fieldName] : ["display_name"];
            field.records = await this.services.orm.searchRead(
                field.relation,
                field.domain || [],
                fieldNames
            );
            if (field.fieldName) {
                field.records.forEach((r) => (r["display_name"] = r[field.fieldName]));
            }
        }
        return field.records;
    }
    async prepareFormModel(el, activeForm) {
        const formKey = activeForm.website_form_key;
        const formInfo = registry.category("website.form_editor_actions").get(formKey, null);
        if (formInfo) {
            const formatInfo = getDefaultFormat(el);
            await formInfo.formFields.forEach(async (field) => {
                field.formatInfo = formatInfo;
                await this.fetchFieldRecords(field);
            });
            await this.fetchFormInfoFields(formInfo);
        }
        return formInfo;
    }
    /**
     * Add a hidden field to the form
     *
     * @param {HTMLElement} el
     * @param {string} value
     * @param {string} fieldName
     */
    addHiddenField(el, value, fieldName) {
        for (const hiddenEl of el.querySelectorAll(
            `.s_website_form_dnone:has(input[name="${fieldName}"])`
        )) {
            hiddenEl.remove();
        }
        // For the email_to field, we keep the field even if it has no value so
        // that the email is sent to data-for value or to the default email.
        if (fieldName === "email_to" && !value && !this.dataForEmailTo) {
            value = this.defaultEmailToValue;
        }
        if (value || fieldName === "email_to") {
            const hiddenField = renderToElement("website.form_field_hidden", {
                field: {
                    name: fieldName,
                    value: value,
                    dnone: true,
                    formatInfo: {},
                },
            });
            el.querySelector(".s_website_form_submit").insertAdjacentElement(
                "beforebegin",
                hiddenField
            );
        }
    }
    /**
     * Apply the model on the form changing its fields
     *
     * @param {HTMLElement} el
     * @param {Object} activeForm
     * @param {Integer} modelId
     * @param {Object} formInfo obtained from prepareFormModel
     */
    applyFormModel(el, activeForm, modelId, formInfo) {
        let oldFormInfo;
        if (modelId) {
            const oldFormKey = activeForm.website_form_key;
            if (oldFormKey) {
                oldFormInfo = registry
                    .category("website.form_editor_actions")
                    .get(oldFormKey, null);
            }
            for (const fieldEl of el.querySelectorAll(".s_website_form_field")) {
                fieldEl.remove();
            }
            activeForm = this.modelsCache.get().find((model) => model.id === modelId);
        }
        // Success page
        if (!el.dataset.successMode) {
            el.dataset.successMode = "redirect";
        }
        if (el.dataset.successMode === "redirect") {
            const currentSuccessPage = el.dataset.successPage;
            if (formInfo && formInfo.successPage) {
                el.dataset.successPage = formInfo.successPage;
            } else if (
                !oldFormInfo ||
                (oldFormInfo !== formInfo &&
                    oldFormInfo.successPage &&
                    currentSuccessPage === oldFormInfo.successPage)
            ) {
                el.dataset.successPage = "/contactus-thank-you";
            }
        }
        // Model name
        el.dataset.model_name = activeForm.model;
        // Load template
        if (formInfo) {
            const formatInfo = getDefaultFormat(el);
            formInfo.formFields.forEach((field) => {
                field.formatInfo = formatInfo;
                const locationEl = el.querySelector(
                    ".s_website_form_submit, .s_website_form_recaptcha"
                );
                locationEl.insertAdjacentElement("beforebegin", renderField(field));
            });
        }
    }
    /**
     * Ensures formInfo fields are fetched.
     */
    async fetchFormInfoFields(formInfo) {
        if (formInfo.fields) {
            const proms = formInfo.fields.map((field) => this.fetchFieldRecords(field));
            await Promise.all(proms);
        }
    }
    async fetchAuthorizedFields(formEl) {
        // Combine model and fields into cache key.
        const model = formEl.dataset.model_name;
        const propertyOrigins = {};
        const parts = [model];
        for (const hiddenInputEl of [...formEl.querySelectorAll("input[type=hidden]")].sort(
            (firstEl, secondEl) => firstEl.name.localeCompare(secondEl.name)
        )) {
            // Pushing using the name order to avoid being impacted by the
            // order of hidden fields within the DOM.
            parts.push(hiddenInputEl.name);
            parts.push(hiddenInputEl.value);
            propertyOrigins[hiddenInputEl.name] = hiddenInputEl.value;
        }
        const cacheKey = parts.join("/");
        return this.authorizedFieldsCache.read({ cacheKey, model, propertyOrigins });
    }
    async _fetchAuthorizedFields({ cacheKey, model, propertyOrigins }) {
        return this.services.orm.call("ir.model", "get_authorized_fields", [
            model,
            propertyOrigins,
        ]);
    }
    /**
     * Set the correct mark on all fields.
     */
    setLabelsMark(formEl) {
        formEl.querySelectorAll(".s_website_form_mark").forEach((el) => el.remove());
        const mark = getMark(formEl);
        if (!mark) {
            return;
        }
        let fieldsToMark = [];
        const requiredSelector = ".s_website_form_model_required, .s_website_form_required";
        const fields = Array.from(formEl.querySelectorAll(".s_website_form_field"));
        if (isRequiredMark(formEl)) {
            fieldsToMark = fields.filter((el) => el.matches(requiredSelector));
        } else if (isOptionalMark(formEl)) {
            fieldsToMark = fields.filter((el) => !el.matches(requiredSelector));
        }
        fieldsToMark.forEach((field) => {
            const span = document.createElement("span");
            span.classList.add("s_website_form_mark");
            span.textContent = ` ${mark}`;
            field.querySelector(".s_website_form_label").appendChild(span);
        });
    }
    addFieldToForm(formEl) {
        const field = getCustomField("char", _t("Custom Text"));
        field.formatInfo = getDefaultFormat(formEl);
        const fieldEl = renderField(field);
        const locationEl = formEl.querySelector(
            ".s_website_form_submit, .s_website_form_recaptcha"
        );
        locationEl.insertAdjacentElement("beforebegin", fieldEl);
        this.dependencies["builder-options"].updateContainers(fieldEl);
    }
    addFieldAfterField(fieldEl) {
        const formEl = fieldEl.closest("form");
        const field = getCustomField("char", _t("Custom Text"));
        field.formatInfo = getFieldFormat(fieldEl);
        field.formatInfo.requiredMark = isRequiredMark(formEl);
        field.formatInfo.optionalMark = isOptionalMark(formEl);
        field.formatInfo.mark = getMark(formEl);
        const newFieldEl = renderField(field);
        fieldEl.insertAdjacentElement("afterend", newFieldEl);
        this.dependencies["builder-options"].updateContainers(newFieldEl);
    }
}

registry.category("website-plugins").add(FormOptionPlugin.id, FormOptionPlugin);
