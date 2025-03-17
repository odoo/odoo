import { registry } from "@web/core/registry";
import { Cache } from "@web/core/utils/cache";
import { Plugin } from "@html_editor/plugin";
import { reactive } from "@odoo/owl";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { FormOption } from "./form_option";
import { FormFieldOptionRedraw } from "./form_field_option_redraw";
import { FormOptionAddFieldButton } from "./form_option_add_field_button";
import {
    deleteConditionalVisibility,
    findCircular,
    getActiveField,
    getCustomField,
    getDefaultFormat,
    getDependencyEl,
    getDomain,
    getFieldFormat,
    getFieldName,
    getFieldType,
    getLabelPosition,
    getMark,
    getMultipleInputs,
    getNewRecordId,
    getQuotesEncodedName,
    getSelect,
    isFieldCustom,
    isOptionalMark,
    isRequiredMark,
    renderField,
    replaceFieldElement,
    setActiveProperties,
    setVisibilityDependency,
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
            {
                OptionComponent: FormFieldOptionRedraw,
                props: {
                    loadFieldOptionData: this.loadFieldOptionData.bind(this),
                },
                selector: ".s_website_form_field",
                exclude: ".s_website_form_dnone",
            },
            {
                template: "html_builder.website.s_website_form_submit_option",
                selector: ".s_website_form_submit",
                exclude: ".s_website_form_no_submit_options",
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
            // Form actions
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
            // Field actions
            customField: {
                load: this.prepareFields.bind(this),
                apply: ({ editingElement: fieldEl, value, loadResult: fields }) => {
                    const oldLabelText = fieldEl.querySelector(
                        ".s_website_form_label_content"
                    ).textContent;
                    const field = getCustomField(value, oldLabelText);
                    setActiveProperties(fieldEl, field);
                    this.replaceField(fieldEl, field, fields);
                },
                isApplied: ({ editingElement: fieldEl, value }) => {
                    const currentValue = isFieldCustom(fieldEl) ? getFieldType(fieldEl) : "";
                    return currentValue === value;
                },
            },
            existingField: {
                load: this.prepareFields.bind(this),
                apply: ({ editingElement: fieldEl, value, loadResult: fields }) => {
                    const field = fields[value];
                    setActiveProperties(fieldEl, field);
                    this.replaceField(fieldEl, field, fields);
                },
                isApplied: ({ editingElement: fieldEl, value }) => {
                    const currentValue = isFieldCustom(fieldEl) ? "" : getFieldName(fieldEl);
                    return currentValue === value;
                },
            },
            selectType: {
                load: this.prepareFields.bind(this),
                apply: ({ editingElement: fieldEl, value, loadResult: fields }) => {
                    const field = getActiveField(fieldEl, { fields });
                    field.type = value;
                    this.replaceField(fieldEl, field, fields);
                },
                isApplied: ({ editingElement: fieldEl, value }) => {
                    const currentValue = getFieldType(fieldEl);
                    return currentValue === value;
                },
            },
            existingFieldSelectType: {
                load: this.prepareFields.bind(this),
                apply: ({ editingElement: fieldEl, value, loadResult: fields }) => {
                    const field = getActiveField(fieldEl, { fields });
                    field.type = value;
                    this.replaceField(fieldEl, field, fields);
                },
                isApplied: ({ editingElement: fieldEl, value }) => {
                    const currentValue = getFieldType(fieldEl);
                    return currentValue === value;
                },
            },
            multiCheckboxDisplay: {
                apply: ({ editingElement: fieldEl, value }) => {
                    const targetEl = getMultipleInputs(fieldEl);
                    const isHorizontal = value === "horizontal";
                    for (const el of targetEl.querySelectorAll(".checkbox, .radio")) {
                        el.classList.toggle("col-lg-4", isHorizontal);
                        el.classList.toggle("col-md-6", isHorizontal);
                    }
                    targetEl.dataset.display = value;
                },
                isApplied: ({ editingElement: fieldEl, value }) => {
                    const targetEl = getMultipleInputs(fieldEl);
                    const currentValue = targetEl ? targetEl.dataset.display : "";
                    return currentValue === value;
                },
            },
            setLabelText: {
                apply: ({ editingElement: fieldEl, value }) => {
                    const labelEl = fieldEl.querySelector(".s_website_form_label_content");
                    labelEl.textContent = value;
                    if (isFieldCustom(fieldEl)) {
                        value = getQuotesEncodedName(value);
                        const multiple = fieldEl.querySelector(".s_website_form_multiple");
                        if (multiple) {
                            multiple.dataset.name = value;
                        }
                        const inputEls = fieldEl.querySelectorAll(".s_website_form_input");
                        const previousInputName = fieldEl.name;
                        inputEls.forEach((el) => (el.name = value));

                        // Synchronize the fields whose visibility depends on this field
                        const dependentEls = fieldEl
                            .closest("form")
                            .querySelectorAll(
                                `.s_website_form_field[data-visibility-dependency="${CSS.escape(
                                    previousInputName
                                )}"]`
                            );
                        for (const dependentEl of dependentEls) {
                            if (findCircular(fieldEl, dependentEl)) {
                                // For all the fields whose visibility depends on this
                                // field, check if the new name creates a circular
                                // dependency and remove the problematic conditional
                                // visibility if it is the case. E.g. a field (A) depends on
                                // another (B) and the user renames "B" by "A".
                                deleteConditionalVisibility(dependentEl);
                            } else {
                                dependentEl.dataset.visibilityDependency = value;
                            }
                        }
                        /* TODO: make sure this is handled on non-preview:
                        if (!previewMode) {
                            // TODO: @owl-options is this still true ?
                            // As the field label changed, the list of available visibility
                            // dependencies needs to be updated in order to not propose a
                            // field that would create a circular dependency.
                            this.rerender = true;
                        }
                        */
                    }
                },
                getValue: ({ editingElement: fieldEl }) => {
                    const labelEl = fieldEl.querySelector(".s_website_form_label_content");
                    return labelEl.textContent;
                },
            },
            selectLabelPosition: {
                load: this.prepareFields.bind(this),
                apply: ({ editingElement: fieldEl, value, loadResult: fields }) => {
                    const field = getActiveField(fieldEl, { fields });
                    field.formatInfo.labelPosition = value;
                    this.replaceField(fieldEl, field, fields);
                },
                isApplied: ({ editingElement: fieldEl, value }) => {
                    const currentValue = getLabelPosition(fieldEl);
                    return currentValue === value;
                },
            },
            toggleDescription: {
                load: this.prepareFields.bind(this),
                apply: ({ editingElement: fieldEl, loadResult: fields, value }) => {
                    const description = fieldEl.querySelector(".s_website_form_field_description");
                    const hasDescription = !!description;
                    const field = getActiveField(fieldEl, { fields });
                    field.description = !hasDescription; // Will be changed to default description in qweb
                    this.replaceField(fieldEl, field, fields);
                },
                isApplied: ({ editingElement: fieldEl }) => {
                    const description = fieldEl.querySelector(".s_website_form_field_description");
                    return !!description;
                },
            },
            selectTextareaValue: {
                apply: ({ editingElement: fieldEl, value }) => {
                    fieldEl.textContent = value;
                    fieldEl.value = value;
                },
                getValue: ({ editingElement: fieldEl }) => fieldEl.textContent,
            },
            toggleRequired: {
                apply: ({ editingElement: fieldEl, param: { mainParam: activeValue } }) => {
                    fieldEl.classList.add(activeValue);
                    fieldEl
                        .querySelectorAll("input, select, textarea")
                        .forEach((el) => el.toggleAttribute("required", true));
                    this.setLabelsMark(fieldEl.closest("form"));
                },
                clean: ({ editingElement: fieldEl, param: { mainParam: activeValue } }) => {
                    fieldEl.classList.remove(activeValue);
                    fieldEl
                        .querySelectorAll("input, select, textarea")
                        .forEach((el) => el.removeAttribute("required"));
                    this.setLabelsMark(fieldEl.closest("form"));
                },
                isApplied: ({ editingElement: fieldEl, param: { mainParam: activeValue } }) =>
                    fieldEl.classList.contains(activeValue),
            },
            setVisibility: {
                load: this.prepareConditionInputs.bind(this),
                apply: ({ editingElement: fieldEl, value, loadResult: conditionInputs }) => {
                    if (value === "conditional") {
                        for (const conditionInput of conditionInputs) {
                            if (conditionInput.name) {
                                // Set a default visibility dependency
                                setVisibilityDependency(fieldEl, conditionInput.name);
                                return;
                            }
                        }
                        this.services.dialog.add(ConfirmationDialog, {
                            body: _t("There is no field available for this option."),
                        });
                    }
                    deleteConditionalVisibility(fieldEl);
                },
                isApplied: () => true,
            },
            setVisibilityDependency: {
                apply: ({ editingElement: fieldEl, value }) => {
                    setVisibilityDependency(fieldEl, value);
                },
                isApplied: ({ editingElement: fieldEl, value }) => {
                    const currentValue = fieldEl.dataset.visibilityDependency || "";
                    return currentValue === value;
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
        // TODO remove this - put there to avoid crash
        if (!field) {
            return;
        }
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
    /**
     * To be used in load for any action that uses getActiveField or
     * replaceField
     */
    async prepareFields({ editingElement: fieldEl, value }) {
        // TODO Through cache ?
        const fieldOptionData = await this.loadFieldOptionData(fieldEl);
        const fieldName = getFieldName(fieldEl);
        const field = fieldOptionData.fields[fieldName];
        await this.fetchFieldRecords(field);
        if (fieldOptionData.fields[value]) {
            await this.fetchFieldRecords(fieldOptionData.fields[value]);
        }
        return fieldOptionData.fields;
    }
    async prepareConditionInputs({ editingElement: fieldEl, value }) {
        // TODO Through cache ?
        const fieldOptionData = await this.loadFieldOptionData(fieldEl);
        const fieldName = getFieldName(fieldEl);
        const field = fieldOptionData.fields[fieldName];
        await this.fetchFieldRecords(field);
        if (fieldOptionData.fields[value]) {
            await this.fetchFieldRecords(fieldOptionData.fields[value]);
        }
        return fieldOptionData.conditionInputs;
    }
    /**
     * Replaces the old field content with the field provided.
     *
     * @param {HTMLElement} oldFieldEl
     * @param {Object} field
     * @param {Array} fields
     * @returns {Promise}
     */
    replaceField(oldFieldEl, field, fields) {
        const activeField = getActiveField(oldFieldEl, { fields });
        if (activeField.type !== field.type) {
            field.value = "";
        }
        const targetEl = oldFieldEl.querySelector(".s_website_form_input");
        if (targetEl) {
            if (["checkbox", "radio"].includes(targetEl.getAttribute("type"))) {
                // Remove first checkbox/radio's id's final '0'.
                field.id = targetEl.id.slice(0, -1);
            } else {
                field.id = targetEl.id;
            }
        }
        const fieldEl = renderField(field);
        replaceFieldElement(oldFieldEl, fieldEl);
    }
    async loadFieldOptionData(fieldEl) {
        const formEl = fieldEl.closest("form");
        const fields = {};
        // Get the authorized existing fields for the form model
        // Do it on each render because of custom property fields which can
        // change depending on the project selected.
        const existingFields = await this.fetchAuthorizedFields(formEl).then((fieldsFromCache) => {
            for (const [fieldName, field] of Object.entries(fieldsFromCache)) {
                field.name = fieldName;
                const fieldDomain = getDomain(formEl, field.name, field.type, field.relation);
                field.domain = fieldDomain || field.domain || [];
                fields[fieldName] = field;
            }
            return Object.keys(fieldsFromCache)
                .map((key) => {
                    const field = fieldsFromCache[key];
                    return {
                        name: field.name,
                        string: field.string,
                    };
                })
                .sort((a, b) =>
                    a.string.localeCompare(b.string, undefined, {
                        numeric: true,
                        sensitivity: "base",
                    })
                );
        });
        // Update available visibility dependencies
        const existingDependencyNames = [];
        const conditionInputs = [];
        for (const el of formEl.querySelectorAll(
            ".s_website_form_field:not(.s_website_form_dnone)"
        )) {
            const inputEl = el.querySelector(".s_website_form_input");
            if (
                el.querySelector(".s_website_form_label_content") &&
                inputEl &&
                inputEl.name &&
                inputEl.name !== fieldEl.querySelector(".s_website_form_input").name &&
                !existingDependencyNames.includes(inputEl.name) &&
                !findCircular(el, fieldEl)
            ) {
                conditionInputs.push({
                    name: inputEl.name,
                    textContent: el.querySelector(".s_website_form_label_content").textContent,
                });
                existingDependencyNames.push(inputEl.name);
            }
        }

        const comparator = fieldEl.dataset.visibilityComparator;
        const dependencyEl = getDependencyEl(fieldEl);
        const conditionValueList = [];
        if (dependencyEl) {
            if (
                ["radio", "checkbox"].includes(dependencyEl.type) ||
                dependencyEl.nodeName === "SELECT"
            ) {
                // Update available visibility options
                const inputContainerEl = fieldEl;
                if (dependencyEl.nodeName === "SELECT") {
                    for (const option of dependencyEl.querySelectorAll("option")) {
                        conditionValueList.push({
                            value: option.value,
                            textContent: option.textContent || `<${_t("no value")}>`,
                        });
                    }
                    if (!inputContainerEl.dataset.visibilityCondition) {
                        inputContainerEl.dataset.visibilityCondition =
                            dependencyEl.querySelector("option").value;
                    }
                } else {
                    // DependencyEl is a radio or a checkbox
                    const dependencyContainerEl = dependencyEl.closest(".s_website_form_field");
                    const inputsInDependencyContainer =
                        dependencyContainerEl.querySelectorAll(".s_website_form_input");
                    // TODO: @owl-options already wrong in master for e.g. Project/Tags
                    for (const el of inputsInDependencyContainer) {
                        conditionValueList.push({
                            value: el.value,
                            textContent: el.value,
                        });
                    }
                    if (!inputContainerEl.dataset.visibilityCondition) {
                        inputContainerEl.dataset.visibilityCondition =
                            inputsInDependencyContainer[0].value;
                    }
                }
                if (!inputContainerEl.dataset.visibilityComparator) {
                    inputContainerEl.dataset.visibilityComparator = "selected";
                }
            }
            if (!comparator) {
                // Set a default comparator according to the type of dependency
                if (dependencyEl.dataset.target) {
                    fieldEl.dataset.visibilityComparator = "after";
                } else if (
                    ["text", "email", "tel", "url", "search", "password", "number"].includes(
                        dependencyEl.type
                    ) ||
                    dependencyEl.nodeName === "TEXTAREA"
                ) {
                    fieldEl.dataset.visibilityComparator = "equal";
                } else if (dependencyEl.type === "file") {
                    fieldEl.dataset.visibilityComparator = "fileSet";
                }
            }
        }

        const currentFieldName = getFieldName(fieldEl);
        const fieldsInForm = Array.from(
            formEl.querySelectorAll(
                ".s_website_form_field:not(.s_website_form_custom) .s_website_form_input"
            )
        )
            .map((el) => el.name)
            .filter((el) => el !== currentFieldName);
        const availableFields = existingFields.filter(
            (field) => !fieldsInForm.includes(field.name)
        );

        const selectEl = getSelect(fieldEl);
        const multipleInputsEl = getMultipleInputs(fieldEl);
        let valueList = undefined;
        if (selectEl || multipleInputsEl) {
            const field = Object.assign({}, fields[getFieldName(fieldEl)]);
            const type = getFieldType(fieldEl);

            const optionText = selectEl
                ? "Option"
                : type === "selection"
                ? _t("Radio")
                : _t("Checkbox");
            const defaults = [...fieldEl.querySelectorAll("[checked], [selected]")].map((el) =>
                /^-?[0-9]{1,15}$/.test(el.value) ? parseInt(el.value) : el.value
            );
            let availableRecords = undefined;
            if (!isFieldCustom(fieldEl)) {
                await this.fetchFieldRecords(field);
                availableRecords = JSON.stringify(field.records);
            }
            valueList = reactive({
                title: _t("%s List", optionText),
                addItemTitle: _t("Add new %s", optionText),
                hasDefault: ["one2many", "many2many"].includes(type) ? "multiple" : "unique",
                defaults: JSON.stringify(defaults),
                availableRecords: availableRecords,
                newRecordId: isFieldCustom(fieldEl) ? getNewRecordId(fieldEl) : "",
            });
        }
        return {
            fields,
            existingFields,
            conditionInputs,
            availableFields,
            valueList,
            conditionValueList,
        };
    }
}

registry.category("website-plugins").add(FormOptionPlugin.id, FormOptionPlugin);
