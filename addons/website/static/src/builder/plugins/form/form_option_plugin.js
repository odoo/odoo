import { registry } from "@web/core/registry";
import { Cache } from "@web/core/utils/cache";
import { Plugin } from "@html_editor/plugin";
import { reactive } from "@odoo/owl";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { redirect } from "@web/core/utils/urls";
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
    getModelName,
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
    getParsedDataFor,
    rerenderField,
} from "./utils";
import { SyncCache } from "@html_builder/utils/sync_cache";
import { _t } from "@web/core/l10n/translation";
import { renderToElement } from "@web/core/utils/render";
import { selectElements } from "@html_editor/utils/dom_traversal";
import { BuilderAction } from "@html_builder/core/builder_action";
import { FormOption } from "./form_option";
import { isSmallInteger } from "@html_builder/utils/utils";
import { localization } from "@web/core/l10n/localization";
import { formatDate } from "@web/core/l10n/dates";
import { BaseOptionComponent } from "@html_builder/core/utils";

const { DateTime } = luxon;

export class WebsiteFormSubmitOption extends BaseOptionComponent {
    static template = "website.s_website_form_submit_option";
    static selector = ".s_website_form_submit";
    static exclude = ".s_website_form_no_submit_options";
}

const DEFAULT_EMAIL_TO_VALUE = "info@yourcompany.example.com";
export class FormOptionPlugin extends Plugin {
    static id = "websiteFormOption";
    static dependencies = ["builderActions", "builderOptions", "savePlugin"];
    static shared = [
        "prepareFormModel",
        "getModelsCache",
        "applyFormModel",
        "addHiddenField",
        "fetchAuthorizedFields",
        "loadFieldOptionData",
        "prepareFields",
        "replaceField",
        "prepareConditionInputs",
        "setLabelsMark",
        "clearValidationDataset",
        "defaultMessage",
        "fetchModels",
    ];
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
        clone_disabled_reason_providers: ({ el, reasons }) => {
            if (
                el.classList.contains("s_website_form_field") &&
                !el.classList.contains("s_website_form_custom")
            ) {
                reasons.push(_t("You cannot duplicate this field."));
            }
            if (el.classList.contains("s_website_form_submit")) {
                reasons.push(_t("You can't duplicate the submit button of the form."));
            }
        },
        remove_disabled_reason_providers: ({ el, reasons }) => {
            if (el.classList.contains("s_website_form_model_required")) {
                reasons.push(
                    _t(
                        "This field is mandatory for this action. You cannot remove it. Try hiding it with the 'Visibility' option instead and add it a default value."
                    )
                );
            }
            if (el.classList.contains("s_website_form_submit")) {
                reasons.push(_t("You can't remove the submit button of the form"));
            }
        },
        builder_options: [FormOption, FormFieldOptionRedraw, WebsiteFormSubmitOption],
        builder_actions: {
            // Form actions
            // Components that use this action MUST await fetchModels before they start.
            SelectAction,
            // Select the value of a field (hidden) that will be used on the model as a preset.
            // ie: The Job you apply for if the form is on that job's page.
            AddActionFieldAction,
            PromptSaveRedirectAction,
            UpdateLabelsMarkAction,
            SetMarkAction,
            OnSuccessAction,
            ToggleEndMessageAction,
            FormToggleRecaptchaLegalAction,
            // Field actions
            CustomFieldAction,
            ExistingFieldAction,
            SelectTypeAction,
            ExistingFieldSelectTypeAction,
            MultiCheckboxDisplayAction,
            SetLabelTextAction,
            SelectLabelPositionAction,
            ToggleDescriptionAction,
            SelectTextareaValueAction,
            ToggleRequiredAction,
            SetVisibilityAction,
            SetVisibilityDependencyAction,
            SetFormCustomFieldValueListAction,
            PropertyAction,
            SetCustomErrorMessageAction,
            SetDefaultErrorMessageAction,
            SetRequirementComparatorAction,
            SetMultipleFilesAction,
        },
        content_not_editable_selectors: ".s_website_form form",
        content_editable_selectors: [
            ".s_website_form_send",
            ".s_website_form_field_description",
            ".s_website_form_recaptcha",
            ".row > div:not(.s_website_form_field, .s_website_form_submit, .s_website_form_field *, .s_website_form_submit *)",
        ].map((selector) => `.s_website_form form ${selector}`),
        clean_for_save_handlers: ({ root: rootEl }) => {
            this.removeSuccessMessagePreviews(rootEl);
        },
        dropzone_selector: [
            {
                selector: ".s_website_form",
                excludeAncestor: "form",
            },
            {
                selector: ".s_website_form_field, .s_website_form_submit",
                exclude: ".s_website_form_dnone",
                dropNear: ".s_website_form_field",
                dropLockWithin: "form",
            },
        ],
        so_content_addition_selector: [".s_website_form"],
        on_snippet_dropped_handlers: this.onSnippetDropped.bind(this),
        on_cloned_handlers: this.onCloned.bind(this),
    };
    setup() {
        this.modelsCache = new SyncCache(this._fetchModels.bind(this));
        this.fieldRecordsCache = new SyncCache(this._fetchFieldRecords.bind(this));
        this.authorizedFieldsCache = new Cache(
            this._fetchAuthorizedFields.bind(this),
            ({ cacheKey }) => cacheKey
        );
        this.visibilityConditionCachedRecords = new Cache(
            this._getVisibilityConditionCachedRecords.bind(this),
            JSON.stringify
        );
    }
    destroy() {
        super.destroy();
        this.modelsCache.invalidate();
        this.fieldRecordsCache.invalidate();
        this.authorizedFieldsCache.invalidate();
        this.visibilityConditionCachedRecords.invalidate();
    }
    getModelsCache(formEl) {
        // Through a method so that it can be overridden.
        return this.modelsCache.get();
    }
    async fetchModels(formEl) {
        return this.modelsCache.preload();
    }
    async _fetchModels() {
        return await this.services.orm.call("ir.model", "get_compatible_form_models");
    }
    async fetchFieldRecords(field) {
        if (field) {
            field.records = await this.fieldRecordsCache.preload(field);
            return field.records;
        }
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
        const formKey = activeForm?.website_form_key;
        const formInfo = registry.category("website.form_editor_actions").get(formKey, null);
        if (formInfo) {
            const formatInfo = getDefaultFormat(el);
            await Promise.all(
                formInfo.formFields.map((field) => {
                    field.formatInfo = formatInfo;
                    return this.fetchFieldRecords(field);
                })
            );
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
            value = DEFAULT_EMAIL_TO_VALUE;
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
            activeForm = this.getModelsCache(el).find((model) => model.id === modelId);
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
                // Create a shallow copy of field to prevent unintended
                // mutations to the original field stored in the registry
                const _field = { ...field };
                _field.formatInfo = formatInfo;
                const locationEl = el.querySelector(
                    ".s_website_form_submit, .s_website_form_recaptcha"
                );
                locationEl.insertAdjacentElement("beforebegin", renderField(_field));
            });
            // Special case: handle hidden fields separately.
            // In some forms (e.g., contact forms), the "email_to" field must be included as hidden.
            // For example, this may force the 'email_to' value to a dummy/default one on the
            // contact us form just by interacting with it.
            formInfo.fields?.forEach(field => {
                if (field.defaultValue) {
                    this.addHiddenField(el, field.defaultValue, field.name);
                }
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
    async _getVisibilityConditionCachedRecords(model, domain, fields, kwargs = {}) {
        return this.services.orm.searchRead(model, domain, fields, {
            ...kwargs,
            limit: 1000, // Safeguard to not crash DBs
        });
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
        let locationEl = formEl.querySelector(
            ".s_website_form_submit, .s_website_form_recaptcha"
        );
        if (!locationEl) {
            locationEl = formEl.querySelector(".s_website_form_rows");
            locationEl.insertAdjacentElement("beforeend", fieldEl);
        } else {
            locationEl.insertAdjacentElement("beforebegin", fieldEl);
        }
        this.dependencies.builderOptions.setNextTarget(fieldEl);
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
        this.dependencies.builderOptions.setNextTarget(newFieldEl);
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

        // Synchronize the possible values with the fields whose visibility
        // depends on the current field
        const newValuesText = field.records ? field.records.map((record) => record.id) : [];
        const inputEls = oldFieldEl.querySelectorAll(".s_website_form_input, option");
        const inputName = oldFieldEl.querySelector(".s_website_form_input")?.name;
        const formEl = oldFieldEl.closest(".s_website_form");
        for (let i = 0; i < inputEls.length; i++) {
            const input = inputEls[i];
            if (newValuesText[i] && input.value && !newValuesText.includes(input.value)) {
                for (const dependentEl of formEl.querySelectorAll(
                    `[data-visibility-condition="${CSS.escape(
                        input.value
                    )}"][data-visibility-dependency="${CSS.escape(inputName)}"]`
                )) {
                    dependentEl.dataset.visibilityCondition = newValuesText[i];
                }
                break;
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
            ".s_website_form_field:not(.s_website_form_dnone), .s_website_form_field[data-type]"
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
            const containerEl = dependencyEl.closest(".s_website_form_field");
            const fieldType = containerEl?.dataset.type;
            if (
                ["radio", "checkbox"].includes(dependencyEl.type) ||
                dependencyEl.nodeName === "SELECT" ||
                fieldType === "record"
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
                } else if (fieldType === "record") {
                    const model = containerEl.dataset.model;
                    const idField = containerEl.dataset.idField || "id";
                    const displayNameField = containerEl.dataset.displayNameField || "display_name";
                    const records = await this.visibilityConditionCachedRecords.read(
                        model,
                        [],
                        [idField, displayNameField]
                    );
                    for (const record of records) {
                        conditionValueList.push({
                            value: String(record[idField]),
                            textContent: record[displayNameField],
                        });
                    }
                    if (!inputContainerEl.dataset.visibilityCondition) {
                        inputContainerEl.dataset.visibilityCondition = String(
                            records[0]?.[idField]
                        );
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
                            textContent:
                                inputsInDependencyContainer.length === 1
                                    ? el.value
                                    : dependencyContainerEl.querySelector(`label[for="${el.id}"]`)
                                          .textContent,
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

            const [optionText, checkType] = selectEl
                ? [_t("Option"), "exclusive_boolean"]
                : type === "selection"
                ? [_t("Radio"), "exclusive_boolean"]
                : [_t("Checkbox"), "boolean"];
            const defaults = [...fieldEl.querySelectorAll("[checked], [selected]")].map((el) =>
                isSmallInteger(el.value) ? parseInt(el.value) : el.value
            );
            let availableRecords = undefined;
            if (!isFieldCustom(fieldEl)) {
                await this.fetchFieldRecords(field);
                availableRecords = JSON.stringify(field.records);
            }
            valueList = reactive({
                title: _t("%s List", optionText),
                addItemTitle: _t("Add"),
                checkType,
                defaultItemName: _t("Item"),
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
    /**
     * Handler called when a snippet is dropped.
     *
     * @param {Object} params
     * @param {HTMLElement} params.snippetEl - The dropped snippet element.
     */
    async onSnippetDropped({ snippetEl }) {
        // Re-render the fields to ensure each field gets a unique ID.
        await this.rerenderFieldsInElement(snippetEl);
    }
    /**
     * Handler called when an element is cloned.
     *
     * @param {Object} params
     * @param {HTMLElement} params.cloneEl - The cloned element.
     */
    async onCloned({ cloneEl }) {
        // Re-render the fields to ensure each field gets a unique ID.
        await this.rerenderFieldsInElement(cloneEl);

        this.removeSuccessMessagePreviews(cloneEl);
    }
    /**
     * Re-renders all valid fields inside the given element to ensure
     * each field gets a unique ID.
     *
     * Handles:
     * - A single field element
     * - A form element
     * - Any container that may include one or more forms
     *
     * @param {HTMLElement} rootEl
     */
    async rerenderFieldsInElement(rootEl) {
        if (rootEl.matches("[data-name='Field']:not(.s_website_form_dnone)")) {
            // The root element is a single field - rerender it directly
            const { fields } = await this.loadFieldOptionData(rootEl);
            rerenderField(rootEl, fields);
        } else {
            // The root element may be a form or contain multiple forms -
            // rerender them all
            for (const formEl of selectElements(rootEl, ".s_website_form")) {
                const formFieldsToRerender = formEl.querySelectorAll(
                    "[data-name='Field']:not(.s_website_form_dnone)"
                );
                if (formFieldsToRerender.length === 0) {
                    continue;
                }
                const { fields } = await this.loadFieldOptionData(formFieldsToRerender[0]);
                for (const fieldEl of formFieldsToRerender) {
                    rerenderField(fieldEl, fields);
                }
            }
        }
    }
    /**
     * Removes all the success form message previews that are in the given root
     * element.
     *
     * @param {HTMLElement} rootEl
     */
    removeSuccessMessagePreviews(rootEl) {
        const toCleanEls = rootEl.querySelectorAll(".o_show_form_success_message");
        toCleanEls.forEach((el) => el.classList.remove("o_show_form_success_message"));
    }
    /**
     * Clear the dataset of the field to avoid keeping old values.
     *
     * @params {HTMLElement} fieldEl - The field element to clear.
     */
    clearValidationDataset(fieldEl) {
        delete fieldEl.dataset.customError;
        delete fieldEl.dataset.errorMessage;
        delete fieldEl.dataset.requirementBetween;
        delete fieldEl.dataset.requirementCondition;
    }

    /**
     * Generates an error message for requirement set on field if validation fails.
     *
     * @param {string} [comparator] The method used to form the error message.
     * @param {string} [condition] The expected value of the field.
     * @param {string} [between] The maximum date value if the comparator is
     *      'between' or '!between'.
     * @returns {string} The default error message.
     */
    defaultMessage(comparator, condition, between, type) {
        const textMessages = {
            contains: _t("This field must include keyword %s.", condition),
            "!contains": _t("This field must not include keyword %s.", condition),
            substring: _t("This field must include keyword %s.", condition),
            "!substring": _t("This field must not include keyword %s.", condition),
            greater: _t("Invalid: field is not greater than %s.", condition),
            less: _t("Invalid: field is not less than %s.", condition),
            "greater or equal": _t("Invalid: field is not greater than or equal to %s.", condition),
            "less or equal": _t("Invalid: field is not less than or equal to %s.", condition),
        };

        if (condition && textMessages[comparator]) {
            return textMessages[comparator];
        }

        if (["date", "datetime"].includes(type)) {
            const format = type === "date" ? localization.dateFormat : localization.dateTimeFormat;
            const start = formatDate(DateTime.fromSeconds(parseInt(condition)), { format });
            const end = formatDate(DateTime.fromSeconds(parseInt(between)), { format });

            const dateMessages = {
                dateEqual: _t(
                    "Entered date or time is not correct! It must be %(start)s (%(format)s).",
                    { start, format }
                ),
                "date!equal": _t(
                    "Entered date or time is not correct! It must not be %(start)s (%(format)s).",
                    { start, format }
                ),
                before: _t(
                    "Entered date or time is not correct! It must be before %(start)s (%(format)s).",
                    { start, format }
                ),
                after: _t(
                    "Entered date or time is not correct! It must be after %(start)s (%(format)s).",
                    { start, format }
                ),
                "equal or before": _t(
                    "Entered date or time is not correct! It must be before or equal to %(start)s (%(format)s).",
                    { start, format }
                ),
                "equal or after": _t(
                    "Entered date or time is not correct! It must be after or equal to %(start)s (%(format)s).",
                    { start, format }
                ),
                between: _t(
                    "Entered date or time is not correct! It must be within %(start)s and %(end)s (%(format)s).",
                    { start, end, format }
                ),
                "!between": _t(
                    "Entered date or time is not correct! It must not be within %(start)s and %(end)s (%(format)s).",
                    { start, end, format }
                ),
            };

            if (condition && dateMessages[comparator]) {
                return dateMessages[comparator];
            }
        }

        return _t("An error has occurred, the form has not been sent.");
    }
}

// Form actions
// Components that use this action MUST await fetchModels before they start.
export class SelectAction extends BuilderAction {
    static id = "selectAction";
    static dependencies = ["websiteFormOption"];
    async load({ editingElement: el, value: modelId }) {
        const modelCantChange = !!el.getAttribute("hide-change-model");
        if (modelCantChange) {
            return;
        }
        const activeForm = this.dependencies.websiteFormOption
            .getModelsCache(el)
            .find((model) => model.id === parseInt(modelId));
        return {
            formInfo: await this.dependencies.websiteFormOption.prepareFormModel(el, activeForm),
        };
    }
    apply({ editingElement: el, value: modelId, loadResult }) {
        if (!loadResult) {
            return;
        }
        const models = this.dependencies.websiteFormOption.getModelsCache(el);
        const targetModelName = getModelName(el);
        const activeForm = models.find((m) => m.model === targetModelName);
        this.dependencies.websiteFormOption.applyFormModel(
            el,
            activeForm,
            parseInt(modelId),
            loadResult.formInfo
        );
    }
    isApplied({ editingElement: el, value: modelId }) {
        const models = this.dependencies.websiteFormOption.getModelsCache(el);
        const targetModelName = getModelName(el);
        const activeForm = models.find((m) => m.model === targetModelName);
        return parseInt(modelId) === activeForm.id;
    }
}
// Select the value of a field (hidden) that will be used on the model as a preset.
// ie: The Job you apply for if the form is on that job's page.
export class AddActionFieldAction extends BuilderAction {
    static id = "addActionField";
    static dependencies = ["websiteFormOption"];
    async load({ editingElement: el }) {
        return this.dependencies.websiteFormOption.fetchAuthorizedFields(el);
    }
    apply({ editingElement: el, value, params, loadResult: authorizedFields }) {
        // Remove old property fields.
        for (const [fieldName, field] of Object.entries(authorizedFields)) {
            if (field._property) {
                for (const inputEl of el.querySelectorAll(`[name="${fieldName}"]`)) {
                    inputEl.closest(".s_website_form_field").remove();
                }
            }
        }
        const fieldName = params.fieldName;
        if (params.isSelect === "true") {
            value = parseInt(value);
        }
        this.dependencies.websiteFormOption.addHiddenField(el, value, fieldName);
    }
    // TODO clear ? if field is a boolean ?
    getValue({ editingElement: el, params }) {
        const value = el.querySelector(
            `.s_website_form_dnone input[name="${params.fieldName}"]`
        )?.value;
        if (params.fieldName === "email_to") {
            // For email_to, we try to find a value in this order:
            // 1. The current value of the input
            // 2. The data-for value if it exists
            // 3. The default value (`defaultEmailToValue`)
            if (value && value !== DEFAULT_EMAIL_TO_VALUE) {
                return value;
            }
            // Get the email_to value from the data-for attribute if it exists.
            // We use it if there is no value on the email_to input.
            const formId = el.id;
            const dataForValues = getParsedDataFor(formId, el.ownerDocument);
            return dataForValues?.["email_to"] || DEFAULT_EMAIL_TO_VALUE;
        }
        if (value) {
            return value;
        } else {
            return params.isSelect ? "0" : "";
        }
    }
    isApplied({ editingElement, params, value }) {
        const currentValue = this.getValue({
            editingElement,
            params,
        });
        return currentValue === value;
    }
}
export class PromptSaveRedirectAction extends BuilderAction {
    static id = "promptSaveRedirect";
    static dependencies = ["savePlugin"];
    apply({ params: { mainParam } }) {
        const redirectToAction = (action) => {
            redirect(`/odoo/action-${encodeURIComponent(action)}`);
        };
        new Promise((resolve) => {
            const message = _t("You are about to be redirected. Your changes will be saved.");
            this.services.dialog.add(ConfirmationDialog, {
                body: message,
                confirmLabel: _t("Save and Redirect"),
                confirm: async () => {
                    await this.dependencies.savePlugin.save();
                    await this.config.closeEditor();
                    redirectToAction(mainParam);
                    resolve();
                },
                cancel: () => resolve(),
            });
        });
    }
}
export class UpdateLabelsMarkAction extends BuilderAction {
    static id = "updateLabelsMark";
    static dependencies = ["websiteFormOption"];
    apply({ editingElement: el }) {
        this.dependencies.websiteFormOption.setLabelsMark(el);
    }
    isApplied() {
        return true;
    }
}

export class SetMarkAction extends BuilderAction {
    static id = "setMark";
    static dependencies = ["websiteFormOption"];
    apply({ editingElement: el, value }) {
        el.dataset.mark = value.trim();
        this.dependencies.websiteFormOption.setLabelsMark(el);
    }
    getValue({ editingElement: el }) {
        const mark = getMark(el);
        return mark;
    }
}

export class OnSuccessAction extends BuilderAction {
    static id = "onSuccess";
    apply({ editingElement: el, value }) {
        el.dataset.successMode = value;
        let messageEl = el.parentElement.querySelector(".s_website_form_end_message");
        if (value === "message") {
            if (!messageEl) {
                messageEl = renderToElement("website.s_website_form_end_message");
                el.insertAdjacentElement("afterend", messageEl);
            }
        } else {
            messageEl?.remove();
            messageEl?.classList.remove("o_show_form_success_message");
            el.classList.remove("o_show_form_success_message");
        }
    }
    isApplied({ editingElement: el, value }) {
        const currentValue = el.dataset.successMode;
        return currentValue === value;
    }
}
export class ToggleEndMessageAction extends BuilderAction {
    static id = "toggleEndMessage";
    static dependencies = ["builderOptions"];
    apply({ editingElement: el }) {
        const messageEl = el.parentElement.querySelector(".s_website_form_end_message");
        messageEl.classList.add("o_show_form_success_message");
        el.classList.add("o_show_form_success_message");
        this.dependencies.builderOptions.setNextTarget(messageEl);
    }
    clean({ editingElement: el }) {
        const messageEl = el.parentElement.querySelector(".s_website_form_end_message");
        messageEl.classList.remove("o_show_form_success_message");
        el.classList.remove("o_show_form_success_message");
        this.dependencies.builderOptions.setNextTarget(el);
    }
    isApplied({ editingElement: el, value }) {
        return el.classList.contains("o_show_form_success_message");
    }
}
export class FormToggleRecaptchaLegalAction extends BuilderAction {
    static id = "formToggleRecaptchaLegal";
    apply({ editingElement: el }) {
        const labelWidth = el.querySelector(".s_website_form_label").style.width;
        const legalEl = renderToElement("website.s_website_form_recaptcha_legal", {
            labelWidth: labelWidth,
        });
        legalEl.setAttribute("contentEditable", true);
        el.querySelector(".s_website_form_submit").insertAdjacentElement("beforebegin", legalEl);
    }
    clean({ editingElement: el }) {
        const recaptchaLegalEl = el.querySelector(".s_website_form_recaptcha");
        recaptchaLegalEl.remove();
    }
    isApplied({ editingElement: el }) {
        const recaptchaLegalEl = el.querySelector(".s_website_form_recaptcha");
        return !!recaptchaLegalEl;
    }
}
// Field actions
export class CustomFieldAction extends BuilderAction {
    static id = "customField";
    static dependencies = ["websiteFormOption"];
    load(context) {
        return this.dependencies.websiteFormOption.prepareFields(context);
    }
    apply({ editingElement: fieldEl, value, loadResult: fields }) {
        this.dependencies.websiteFormOption.clearValidationDataset(fieldEl);
        delete fieldEl.dataset.requirementComparator;
        const oldLabelText = fieldEl.querySelector(".s_website_form_label_content").textContent;
        const field = getCustomField(value, oldLabelText);
        setActiveProperties(fieldEl, field);
        this.dependencies.websiteFormOption.replaceField(fieldEl, field, fields);
    }
    isApplied({ editingElement: fieldEl, value }) {
        const currentValue = isFieldCustom(fieldEl) ? getFieldType(fieldEl) : "";
        return currentValue === value;
    }
}
export class ExistingFieldAction extends BuilderAction {
    static id = "existingField";
    static dependencies = ["websiteFormOption"];
    load(context) {
        return this.dependencies.websiteFormOption.prepareFields(context);
    }
    apply({ editingElement: fieldEl, value, loadResult: fields }) {
        const field = fields[value];
        setActiveProperties(fieldEl, field);
        this.dependencies.websiteFormOption.replaceField(fieldEl, field, fields);
    }
    isApplied({ editingElement: fieldEl, value }) {
        const currentValue = isFieldCustom(fieldEl) ? "" : getFieldName(fieldEl);
        return currentValue === value;
    }
}
export class SelectTypeAction extends BuilderAction {
    static id = "selectType";
    static dependencies = ["websiteFormOption"];
    load(context) {
        return this.dependencies.websiteFormOption.prepareFields(context);
    }
    apply({ editingElement: fieldEl, value, loadResult: fields }) {
        const field = getActiveField(fieldEl, { fields });
        field.type = value;
        this.dependencies.websiteFormOption.replaceField(fieldEl, field, fields);
    }
    isApplied({ editingElement: fieldEl, value }) {
        const currentValue = getFieldType(fieldEl);
        return currentValue === value;
    }
}
export class ExistingFieldSelectTypeAction extends BuilderAction {
    static id = "existingFieldSelectType";
    static dependencies = ["websiteFormOption"];
    load(context) {
        return this.dependencies.websiteFormOption.prepareFields(context);
    }
    apply({ editingElement: fieldEl, value, loadResult: fields }) {
        const field = getActiveField(fieldEl, { fields });
        field.type = value;
        this.dependencies.websiteFormOption.replaceField(fieldEl, field, fields);
    }
    isApplied({ editingElement: fieldEl, value }) {
        const currentValue = getFieldType(fieldEl);
        return currentValue === value;
    }
}
export class MultiCheckboxDisplayAction extends BuilderAction {
    static id = "multiCheckboxDisplay";
    apply({ editingElement: fieldEl, value }) {
        const targetEl = getMultipleInputs(fieldEl);
        const isHorizontal = value === "horizontal";
        for (const el of targetEl.querySelectorAll(".checkbox, .radio")) {
            el.classList.toggle("col-lg-4", isHorizontal);
            el.classList.toggle("col-md-6", isHorizontal);
        }
        targetEl.dataset.display = value;
    }
    isApplied({ editingElement: fieldEl, value }) {
        const targetEl = getMultipleInputs(fieldEl);
        const currentValue = targetEl ? targetEl.dataset.display : "";
        return currentValue === value;
    }
}
export class SetLabelTextAction extends BuilderAction {
    static id = "setLabelText";
    static dependencies = ["websiteFormOption"];
    async apply({ editingElement: fieldEl, value }) {
        const labelEl = fieldEl.querySelector(".s_website_form_label_content");
        labelEl.textContent = value;
        if (isFieldCustom(fieldEl)) {
            value = getQuotesEncodedName(value);
            const multiple = fieldEl.querySelector(".s_website_form_multiple");
            if (multiple) {
                multiple.dataset.name = value;
            }
            const inputEls = fieldEl.querySelectorAll(".s_website_form_input");
            const previousInputName = inputEls[0].name;
            inputEls.forEach((el) => (el.name = value));

            // Synchronize the fields whose visibility depends on this field
            const dependentEls = fieldEl.closest("form").querySelectorAll(
                `.s_website_form_field[data-visibility-dependency="${CSS.escape(
                    previousInputName
                )}"],
                    .s_website_form_field[data-visibility-dependency="${CSS.escape(value)}"]`
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
            const fieldWithVisibilityDependencyEls = [
                ...fieldEl.closest("form").querySelectorAll("[data-visibility-dependency]"),
            ];
            await Promise.all(
                fieldWithVisibilityDependencyEls.map(async (fieldWithConditionEl) => {
                    const conditionFieldName = fieldWithConditionEl.dataset.visibilityDependency;
                    const fieldData = await this.dependencies.websiteFormOption.loadFieldOptionData(
                        fieldWithConditionEl
                    );
                    const names = fieldData.conditionInputs.map((entry) => entry.name);
                    if (!names.includes(conditionFieldName)) {
                        deleteConditionalVisibility(fieldWithConditionEl);
                    }
                })
            );
        }
    }
    getValue({ editingElement: fieldEl }) {
        const labelEl = fieldEl.querySelector(".s_website_form_label_content");
        return labelEl.textContent;
    }
}
export class SelectLabelPositionAction extends BuilderAction {
    static id = "selectLabelPosition";
    static dependencies = ["websiteFormOption"];
    load(context) {
        return this.dependencies.websiteFormOption.prepareFields(context);
    }
    apply({ editingElement: fieldEl, value, loadResult: fields }) {
        const field = getActiveField(fieldEl, { fields });
        field.formatInfo.labelPosition = value;
        this.dependencies.websiteFormOption.replaceField(fieldEl, field, fields);
    }
    isApplied({ editingElement: fieldEl, value }) {
        const currentValue = getLabelPosition(fieldEl);
        return currentValue === value;
    }
}
export class ToggleDescriptionAction extends BuilderAction {
    static id = "toggleDescription";
    static dependencies = ["websiteFormOption"];
    load(context) {
        return this.dependencies.websiteFormOption.prepareFields(context);
    }
    apply({ editingElement: fieldEl, loadResult: fields, value }) {
        const description = fieldEl.querySelector(".s_website_form_field_description");
        const hasDescription = !!description;
        const field = getActiveField(fieldEl, { fields });
        field.description = !hasDescription; // Will be changed to default description in qweb
        this.dependencies.websiteFormOption.replaceField(fieldEl, field, fields);
    }
    isApplied({ editingElement: fieldEl }) {
        const description = fieldEl.querySelector(".s_website_form_field_description");
        return !!description;
    }
}
export class SelectTextareaValueAction extends BuilderAction {
    static id = "selectTextareaValue";
    apply({ editingElement: fieldEl, value }) {
        fieldEl.textContent = value;
        fieldEl.value = value;
    }
    getValue({ editingElement: fieldEl }) {
        return fieldEl.textContent;
    }
}
export class ToggleRequiredAction extends BuilderAction {
    static id = "toggleRequired";
    static dependencies = ["websiteFormOption"];
    apply({ editingElement: fieldEl, params: { mainParam: activeValue } }) {
        fieldEl.classList.add(activeValue);
        fieldEl
            .querySelectorAll("input, select, textarea")
            .forEach((el) => el.toggleAttribute("required", true));
        this.dependencies.websiteFormOption.setLabelsMark(fieldEl.closest("form"));
    }
    clean({ editingElement: fieldEl, params: { mainParam: activeValue } }) {
        fieldEl.classList.remove(activeValue);
        fieldEl
            .querySelectorAll("input, select, textarea")
            .forEach((el) => el.removeAttribute("required"));
        this.dependencies.websiteFormOption.setLabelsMark(fieldEl.closest("form"));
    }
    isApplied({ editingElement: fieldEl, params: { mainParam: activeValue } }) {
        return fieldEl.classList.contains(activeValue);
    }
}

/**
 * Custom error message should be visible or not.
 */
export class SetRequirementComparatorAction extends BuilderAction {
    static id = "setRequirementComparator";
    static dependencies = ["websiteFormOption"];
    apply({ editingElement: fieldEl }) {
        this.dependencies.websiteFormOption.clearValidationDataset(fieldEl);
    }
}
/**
 * Sets the dataset value of custom-error attribute which is further used to
 * determine if the input for custom error message should be visible or not.
 *
 * TODO this is basically a toggle whose only purpose is to show more options
 * in the sidebar... its status should not be saved in the website DOM...
 */
export class SetCustomErrorMessageAction extends BuilderAction {
    static id = "setCustomErrorMessage";
    apply({ editingElement: fieldEl }) {
        if (!fieldEl.dataset.customError) {
            fieldEl.dataset.customError = true;
        } else {
            delete fieldEl.dataset.customError;
        }
    }
    isApplied({ editingElement: fieldEl }) {
        return fieldEl.dataset.customError;
    }
}
/**
 * Sets the default error message based on the requirement comparator,
 * condition and type of form fields.
 */
export class SetDefaultErrorMessageAction extends BuilderAction {
    static id = "setDefaultErrorMessage";
    static dependencies = ["websiteFormOption"];
    apply({ editingElement: fieldEl }) {
        const {
            requirementComparator: comparator,
            requirementCondition: condition,
            requirementBetween: between,
            type,
        } = fieldEl.dataset;
        fieldEl.dataset.errorMessage = this.dependencies.websiteFormOption.defaultMessage(
            comparator,
            condition,
            between,
            type
        );
    }
}

export class SetVisibilityAction extends BuilderAction {
    static id = "setVisibility";
    static dependencies = ["websiteFormOption"];
    load(context) {
        return this.dependencies.websiteFormOption.prepareConditionInputs(context);
    }
    apply({ editingElement: fieldEl, value, loadResult: conditionInputs }) {
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
    }
    isApplied() {
        return true;
    }
}
export class SetVisibilityDependencyAction extends BuilderAction {
    static id = "setVisibilityDependency";
    apply({ editingElement: fieldEl, value }) {
        return setVisibilityDependency(fieldEl, value);
    }
    isApplied({ editingElement: fieldEl, value }) {
        const currentValue = fieldEl.dataset.visibilityDependency || "";
        return currentValue === value;
    }
}
export class SetFormCustomFieldValueListAction extends BuilderAction {
    static id = "setFormCustomFieldValueList";
    static dependencies = ["websiteFormOption"];
    load(context) {
        return this.dependencies.websiteFormOption.prepareFields(context);
    }
    apply({ editingElement: fieldEl, value, loadResult: fields }) {
        let valueList = JSON.parse(value);
        if (getSelect(fieldEl)) {
            valueList = valueList.filter((value) => value.id !== "" || value.display_name !== "");
            const hasDefault = valueList.some((value) => value.selected);
            if (valueList.length && !hasDefault) {
                valueList.unshift({
                    id: "",
                    display_name: "",
                    selected: true,
                });
            }
        }
        const field = getActiveField(fieldEl, { fields });
        field.records = valueList;
        this.dependencies.websiteFormOption.replaceField(fieldEl, field, fields);
    }
    getValue({ editingElement: fieldEl }) {
        const fields = [];
        const field = getActiveField(fieldEl, { fields });
        if (
            field.records.length &&
            field.records[0].display_name === "" &&
            field.records[0].selected === true
        ) {
            field.records.shift();
        }
        return JSON.stringify(field.records);
    }
}
class PropertyAction extends BuilderAction {
    static id = "property";

    apply({ editingElement, params: { property, format } = {}, value }) {
        editingElement[property] = format ? format(value) : value;
    }
}
class SetMultipleFilesAction extends BuilderAction {
    static id = "setMultipleFiles";
    apply({ editingElement }) {
        editingElement.multiple = editingElement.dataset.maxFilesNumber > 1;
    }
}

registry.category("website-plugins").add(FormOptionPlugin.id, FormOptionPlugin);
