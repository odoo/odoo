/** @odoo-module **/

import FormEditorRegistry from "@website/js/form_editor_registry";
import {
    SnippetOption,
} from "@web_editor/js/editor/snippets.options";
import { registerContentAdditionSelector } from "@web_editor/js/editor/snippets.registry";
import {
    registerWebsiteOption,
} from "@website/js/editor/snippets.registry";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import weUtils from "@web_editor/js/common/utils";
import "@website/js/editor/snippets.options";
import { unique } from "@web/core/utils/arrays";
import { _t } from "@web/core/l10n/translation";
import { renderToElement } from "@web/core/utils/render";
import { formatDate, formatDateTime } from "@web/core/l10n/dates";
import { session } from "@web/session";
import wUtils from '@website/js/utils';

import { reactive } from "@odoo/owl";

let currentActionName;

const allFormsInfo = new Map();
const clearAllFormsInfo = () => {
    allFormsInfo.clear();
};
/**
 * Returns the domain of a field.
 *
 * @private
 * @param {HTMLElement} formEl
 * @param {String} name
 * @param {String} type
 * @param {String} relation
 * @returns {Object|false}
 */
function _getDomain(formEl, name, type, relation) {
    // We need this because the field domain is in formInfo in the
    // WebsiteFormEditor but we need it in the WebsiteFieldEditor.
    if (!allFormsInfo.get(formEl) || !name || !type || !relation) {
        return false;
    }
    const field = allFormsInfo.get(formEl).fields
        .find(el => el.name === name && el.type === type && el.relation === relation);
    return field && field.domain;
}

const authorizedFieldsCache = {
    data: {},
    /**
     * Returns the fields definitions for a form
     *
     * @param {HTMLElement} formEl
     * @param {Object} orm
     * @returns {Promise}
     */
    get(formEl, orm) {
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
        if (!(cacheKey in this.data)) {
            this.data[cacheKey] = orm.call("ir.model", "get_authorized_fields", [
                model,
                propertyOrigins,
            ]);
        }
        return this.data[cacheKey];
    },
};


export class FormEditor extends SnippetOption {

    //----------------------------------------------------------------------
    // Private
    //----------------------------------------------------------------------

    /**
     * Returns a promise which is resolved once the records of the field
     * have been retrieved.
     *
     * @private
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
            field.records = field.tags.map(tag => ({
                id: tag[0].replaceAll("\\", "\\/").replaceAll(",", "\\,"),
                display_name: tag[1],
            }));
        } else if (field._property && field.comodel) {
            field.records = await this.env.services.orm.searchRead(field.comodel, field.domain || [], ["display_name"]);
        } else if (field.type === "selection") {
            // Set selection as records to avoid added complexity.
            field.records = field.selection.map(el => ({
                id: el[0],
                display_name: el[1],
            }));
        } else if (field.relation && field.relation !== 'ir.attachment') {
            const fieldNames = field.fieldName ? [field.fieldName] : ["display_name"];
            field.records = await this.env.services.orm.searchRead(field.relation, field.domain || [], fieldNames);
            if (field.fieldName) {
                field.records.forEach(r => r["display_name"] = r[field.fieldName]);
            }
        }
        return field.records;
    }
    /**
     * Returns a field object
     *
     * @private
     * @param {string} type the type of the field
     * @param {string} name The name of the field used also as label
     * @returns {Object}
     */
    _getCustomField(type, name) {
        return {
            name: name,
            string: name,
            custom: true,
            type: type,
            // Default values for x2many fields and selection
            records: [{
                id: _t('Option 1'),
                display_name: _t('Option 1'),
            }, {
                id: _t('Option 2'),
                display_name: _t('Option 2'),
            }, {
                id: _t('Option 3'),
                display_name: _t('Option 3'),
            }],
        };
    }
    /**
     * Returns the default formatInfos of a field.
     *
     * @private
     * @returns {Object}
     */
    _getDefaultFormat() {
        return {
            labelWidth: this.$target[0].querySelector('.s_website_form_label').style.width,
            labelPosition: 'left',
            multiPosition: 'horizontal',
            requiredMark: this._isRequiredMark(),
            optionalMark: this._isOptionalMark(),
            mark: this._getMark(),
        };
    }
    /**
     * @private
     * @returns {string}
     */
    _getMark() {
        return this.$target[0].dataset.mark;
    }
    /**
     * Replace all `"` character by `&quot;`.
     *
     * @param {string} name
     * @returns {string}
     */
    _getQuotesEncodedName(name) {
        // Browsers seem to be encoding the double quotation mark character as
        // `%22` (URI encoded version) when used inside an input's name. It is
        // actually quite weird as a sent `<input name='Hello "world" %22'/>`
        // will actually be received as `Hello %22world%22 %22` on the server,
        // making it impossible to know which is actually a real double
        // quotation mark and not the "%22" string. Values do not have this
        // problem: `Hello "world" %22` would be received as-is on the server.
        // In the future, we should consider not using label values as input
        // names anyway; the idea was bad in the first place. We should probably
        // assign random field names (as we do for IDs) and send a mapping
        // with the labels, as values (TODO ?).
        return name.replaceAll(/"/g, character => `&quot;`);
    }
    /**
     * @private
     * @returns {boolean}
     */
    _isOptionalMark() {
        return this.$target[0].classList.contains('o_mark_optional');
    }
    /**
     * @private
     * @returns {boolean}
     */
    _isRequiredMark() {
        return this.$target[0].classList.contains('o_mark_required');
    }
    /**
     * @private
     * @param {Object} field
     * @returns {HTMLElement}
     */
    _renderField(field, resetId = false) {
        if (!field.id) {
            field.id = weUtils.generateHTMLId();
        }
        const params = { field: { ...field } };
        if (["url", "email", "tel"].includes(field.type)) {
            params.field.inputType = field.type;
        }
        if (["boolean", "selection", "binary"].includes(field.type)) {
            params.field.isCheck = true;
        }
        if (field.type === "one2many" && field.relation !== "ir.attachment") {
            params.field.isCheck = true;
        }
        if (field.custom && !field.string) {
            params.field.string = field.name;
        }
        if (field.description) {
            params.default_description = _t("Describe your field here.");
        } else if (["email_cc", "email_to"].includes(field.name)) {
            params.default_description = _t("Separate email addresses with a comma.");
        }
        const template = document.createElement('template');
        const renderType = field.type === "tags" ? "many2many" : field.type;
        template.content.append(renderToElement("website.form_field_" + renderType, params));
        if (field.description && field.description !== true) {
            $(template.content.querySelector('.s_website_form_field_description')).replaceWith(field.description);
        }
        template.content.querySelectorAll('input.datetimepicker-input').forEach(el => el.value = field.propertyValue);
        template.content.querySelectorAll("[name]").forEach(el => {
            el.name = this._getQuotesEncodedName(el.name);
        });
        template.content.querySelectorAll("[data-name]").forEach(el => {
            el.dataset.name = this._getQuotesEncodedName(el.dataset.name);
        });
        return template.content.firstElementChild;
    }
}

export class FieldEditor extends FormEditor {
    static VISIBILITY_DATASET = ['visibilityDependency', 'visibilityCondition', 'visibilityComparator', 'visibilityBetween'];

    /**
     * @override
     */
    willStart() {
        this.formEl = this.$target[0].closest('form');
        return super.willStart(...arguments);
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Returns the target as a field Object
     *
     * @private
     * @param {boolean} noRecords
     * @returns {Object}
     */
    _getActiveField(noRecords) {
        let field;
        const labelText = this.$target.find('.s_website_form_label_content').text();
        if (this._isFieldCustom()) {
            field = this._getCustomField(this.$target[0].dataset.type, labelText);
        } else {
            field = Object.assign({}, this.fields[this._getFieldName()]);
            field.string = labelText;
            field.type = this._getFieldType();
        }
        if (!noRecords) {
            field.records = this._getListItems();
        }
        this._setActiveProperties(field);
        return field;
    }
    /**
     * Returns the format object of a field containing
     * the position, labelWidth and bootstrap col class
     *
     * @private
     * @returns {Object}
     */
    _getFieldFormat() {
        let requiredMark, optionalMark;
        const mark = this.$target[0].querySelector('.s_website_form_mark');
        if (mark) {
            requiredMark = this._isFieldRequired();
            optionalMark = !requiredMark;
        }
        const multipleInput = this._getMultipleInputs();
        const format = {
            labelPosition: this._getLabelPosition(),
            labelWidth: this.$target[0].querySelector('.s_website_form_label').style.width,
            multiPosition: multipleInput && multipleInput.dataset.display || 'horizontal',
            col: [...this.$target[0].classList].filter(el => el.match(/^col-/g)).join(' '),
            requiredMark: requiredMark,
            optionalMark: optionalMark,
            mark: mark && mark.textContent,
        };
        return format;
    }
    /**
     * Returns the name of the field
     *
     * @private
     * @param {HTMLElement} fieldEl
     * @returns {string}
     */
    _getFieldName(fieldEl = this.$target[0]) {
        const multipleName = fieldEl.querySelector('.s_website_form_multiple');
        return multipleName ? multipleName.dataset.name : fieldEl.querySelector('.s_website_form_input').name;
    }
    /**
     * Returns the type of the  field, can be used for both custom and existing fields
     *
     * @private
     * @returns {string}
     */
    _getFieldType() {
        return this.$target[0].dataset.type;
    }
    /**
     * @private
     * @returns {string}
     */
    _getLabelPosition() {
        const label = this.$target[0].querySelector('.s_website_form_label');
        if (this.$target[0].querySelector('.row:not(.s_website_form_multiple)')) {
            return label.classList.contains('text-end') ? 'right' : 'left';
        } else {
            return label.classList.contains('d-none') ? 'none' : 'top';
        }
    }
    /**
     * Returns the multiple checkbox/radio element if it exist else null
     *
     * @private
     * @returns {HTMLElement}
     */
    _getMultipleInputs() {
        return this.$target[0].querySelector('.s_website_form_multiple');
    }
    /**
     * Returns true if the field is a custom field, false if it is an existing field
     *
     * @private
     * @returns {boolean}
     */
    _isFieldCustom() {
        return !!this.$target[0].classList.contains('s_website_form_custom');
    }
    /**
     * Returns true if the field is required by the model or by the user.
     *
     * @private
     * @returns {boolean}
     */
    _isFieldRequired() {
        const classList = this.$target[0].classList;
        return classList.contains('s_website_form_required') || classList.contains('s_website_form_model_required');
    }
    /**
     * Set the active field properties on the field Object
     *
     * @param {Object} field Field to complete with the active field info
     */
    _setActiveProperties(field) {
        const classList = this.$target[0].classList;
        const textarea = this.$target[0].querySelector('textarea');
        const input = this.$target[0].querySelector('input[type="text"], input[type="email"], input[type="number"], input[type="tel"], input[type="url"], textarea');
        const fileInputEl = this.$target[0].querySelector("input[type=file]");
        const description = this.$target[0].querySelector('.s_website_form_field_description');
        field.placeholder = input && input.placeholder;
        if (input) {
            // textarea value has no attribute,  date/datetime timestamp property is formated
            field.value = input.getAttribute('value') || input.value;
        } else if (field.type === 'boolean') {
            field.value = !!this.$target[0].querySelector('input[type="checkbox"][checked]');
        } else if (fileInputEl) {
            field.maxFilesNumber = fileInputEl.dataset.maxFilesNumber;
            field.maxFileSize = fileInputEl.dataset.maxFileSize;
        }
        // property value is needed for date/datetime (formated date).
        field.propertyValue = input && input.value;
        field.description = description && description.outerHTML;
        field.rows = textarea && textarea.rows;
        field.required = classList.contains('s_website_form_required');
        field.modelRequired = classList.contains('s_website_form_model_required');
        field.hidden = classList.contains('s_website_form_field_hidden');
        field.formatInfo = this._getFieldFormat();
    }
}

export class WebsiteFormEditor extends FormEditor {
    /**
     * @override
     */
    async willStart() {
        // Hide change form parameters option for forms
        // e.g. User should not be enable to change existing job application form
        // to opportunity form in 'Apply job' page.
        this.modelCantChange = this.$target.attr('hide-change-model') !== undefined;

        // Get list of website_form compatible models.
        this.models = await this.env.services.orm.call("ir.model", "get_compatible_form_models");

        const targetModelName = this.$target[0].dataset.model_name || 'mail.mail';
        this.activeForm = this.models.find(m => m.model === targetModelName);
        currentActionName = this.activeForm && this.activeForm.website_form_label;

        return super.willStart(...arguments).then(() => {
            return this.start();
        });
    }
    /**
     * @override
     */
    start() {
        const proms = [];
        // Disable text edition
        this.$target.attr('contentEditable', false);
        // Identify editable elements of the form: buttons, description,
        // recaptcha and columns which are not fields.
        const formEditableSelector = [
            ".s_website_form_send",
            ".s_website_form_field_description",
            ".s_website_form_recaptcha",
            ".row > div:not(.s_website_form_field, .s_website_form_submit, .s_website_form_field *, .s_website_form_submit *)",
        ].map(selector => `:scope ${selector}`).join(", ");
        for (const formEditableEl of this.$target[0].querySelectorAll(formEditableSelector)) {
            formEditableEl.contentEditable = "true";
        }
        // Get potential message
        this.$message = this.$target.parent().find('.s_website_form_end_message');
        this.showEndMessage = false;
        // If the form has no model it means a new snippet has been dropped.
        // Apply the default model selected in willStart on it.
        if (!this.$target[0].dataset.model_name) {
            proms.push(this._applyFormModel());
        }
        // Get the email_to value from the data-for attribute if it exists. We
        // use it if there is no value on the email_to input.
        const formId = this.$target[0].id;
        const dataForValues = wUtils.getParsedDataFor(formId, this.$target[0].ownerDocument);
        if (dataForValues) {
            this.dataForEmailTo = dataForValues['email_to'];
        }
        this.defaultEmailToValue = "info@yourcompany.example.com";
        return Promise.all(proms);
    }
    /**
     * @override
     */
    cleanForSave() {
        const model = this.$target[0].dataset.model_name;
        // because apparently this can be called on the wrong widget and
        // we may not have a model, or fields...
        if (model) {
            // we may be re-whitelisting already whitelisted fields. Doesn't
            // really matter.
            const fields = [...this.$target[0].querySelectorAll('.s_website_form_field:not(.s_website_form_custom) .s_website_form_input')].map(el => el.name);
            if (fields.length) {
                // ideally we'd only do this if saving the form
                // succeeds... but no idea how to do that
                this.env.services.orm.call("ir.model.fields", "formbuilder_whitelist", [model, unique(fields)]);
            }
        }
        if (this.$message.length) {
            this.$target.removeClass('d-none');
            this.$message.addClass("d-none");
        }
    }
    /**
     * @override
     */
    async updateUI() {
        await super.updateUI(...arguments);
        // End Message UI
        this.updateUIEndMessage();

        const formKey = this.activeForm.website_form_key;
        const formInfo = FormEditorRegistry.get(formKey, null);
        if (!formInfo || !formInfo.fields) {
            return;
        }
        formInfo.fields.forEach(field => {
            if (field.required) {
                // Try to retrieve hidden value in form, else,
                // get default value or for many2one fields the first option.
                const currentValue = this.$target.find(`.s_website_form_dnone input[name="${field.name}"]`).val();
                const defaultValue = field.defaultValue || field.records[0].id;
                // TODO this code is not rightfully placed (even maybe
                // from the original form feature in older versions). It
                // changes the $target while this method is only about
                // declaring the option UI. This for example forces the
                // 'email_to' value to a dummy value on contact us form just
                // by clicking on it.
                this._addHiddenField(currentValue || defaultValue, field.name);
            }
        });
    }
    /**
     * @see this.updateUI
     */
    updateUIEndMessage() {
        this.$target.toggleClass("d-none", this.showEndMessage);
        this.$message.toggleClass("d-none", !this.showEndMessage);
    }
    /**
     * @override
     */
    notify(name, data) {
        super.notify(...arguments);
        if (name === 'field_mark') {
            this._setLabelsMark();
        } else if (name === 'add_field') {
            const field = this._getCustomField('char', 'Custom Text');
            field.formatInfo = data.formatInfo;
            field.formatInfo.requiredMark = this._isRequiredMark();
            field.formatInfo.optionalMark = this._isOptionalMark();
            field.formatInfo.mark = this._getMark();
            const fieldEl = this._renderField(field);
            data.$target.after(fieldEl);
            this.env.activateSnippet($(fieldEl));
        }
    }

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Select the value of a field (hidden) that will be used on the model as a preset.
     * ie: The Job you apply for if the form is on that job's page.
     */
    addActionField(previewMode, value, params) {
        // Remove old property fields.
        authorizedFieldsCache.get(this.$target[0], this.env.services.orm).then((fields) => {
            for (const [fieldName, field] of Object.entries(fields)) {
                if (field._property) {
                    for (const inputEl of this.$target[0].querySelectorAll(`[name="${fieldName}"]`)) {
                        inputEl.closest(".s_website_form_field").remove();
                    }
                }
            }
        });
        const fieldName = params.fieldName;
        if (params.isSelect === 'true') {
            value = parseInt(value);
        }
        this._addHiddenField(value, fieldName);
        // Existing field editors need to be rebuilt with the correct list of
        // available fields.
        this.env.activateSnippet(this.$target);
    }
    /**
     * Prompts the user to save changes before being redirected
     * towards an action specified in value.
     *
     * @see this.selectClass for parameters
     */
    promptSaveRedirect(name, value, widgetValue) {
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
    }
    /**
     * Changes the onSuccess event.
     */
    onSuccess(previewMode, value, params) {
        this.$target[0].dataset.successMode = value;
        if (value === 'message') {
            if (!this.$message.length) {
                this.$message = $(renderToElement('website.s_website_form_end_message'));
            }
            this.$target.after(this.$message);
        } else {
            this.showEndMessage = false;
            this.$message.remove();
        }
    }
    /**
     * Select the model to create with the form.
     */
    async selectAction(previewMode, value, params) {
        if (this.modelCantChange) {
            return;
        }
        await this._applyFormModel(parseInt(value));
    }
    /**
     * @override
     */
    selectClass(previewMode, value, params) {
        super.selectClass(...arguments);
        if (params.name === 'field_mark_select') {
            this._setLabelsMark();
        }
    }
    /**
     * Set the mark string on the form
     */
    setMark(previewMode, value, params) {
        this.$target[0].dataset.mark = value.trim();
        this._setLabelsMark();
    }
    /**
     * Toggle the recaptcha legal terms
     */
    toggleRecaptchaLegal(previewMode, value, params) {
        const recaptchaLegalEl = this.$target[0].querySelector('.s_website_form_recaptcha');
        if (recaptchaLegalEl) {
            recaptchaLegalEl.remove();
        } else {
            const labelWidth = this.$target[0].querySelector('.s_website_form_label').style.width;
            const legal = renderToElement("website.s_website_form_recaptcha_legal", {
                labelWidth: labelWidth,
            });
            legal.setAttribute('contentEditable', true);
            this.$target.find('.s_website_form_submit').before(legal);
        }
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _computeWidgetState(methodName, params) {
        switch (methodName) {
            case 'selectAction':
                return this.activeForm.id;
            case 'addActionField': {
                const value = this.$target.find(`.s_website_form_dnone input[name="${params.fieldName}"]`).val();
                if (params.fieldName === 'email_to') {
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
                    return params.isSelect ? '0' : '';
                }
            }
            case 'onSuccess':
                return this.$target[0].dataset.successMode;
            case 'setMark':
                return this._getMark();
            case 'toggleRecaptchaLegal':
                return !this.$target[0].querySelector('.s_website_form_recaptcha') || '';
        }
        return super._computeWidgetState(...arguments);
    }
    /**
     * Add a hidden field to the form
     *
     * @private
     * @param {string} value
     * @param {string} fieldName
     */
    _addHiddenField(value, fieldName) {
        this.$target.find(`.s_website_form_dnone:has(input[name="${fieldName}"])`).remove();
        // For the email_to field, we keep the field even if it has no value so
        // that the email is sent to data-for value or to the default email.
        if (fieldName === 'email_to' && !value && !this.dataForEmailTo) {
            value = this.defaultEmailToValue;
        }
        if (value || fieldName === 'email_to') {
            const hiddenField = renderToElement('website.form_field_hidden', {
                field: {
                    name: fieldName,
                    value: value,
                    dnone: true,
                    formatInfo: {},
                },
            });
            this.$target.find('.s_website_form_submit').before(hiddenField);
        }
    }
    /**
     * Apply the model on the form changing it's fields
     *
     * @private
     * @param {Integer} modelId
     */
    async _applyFormModel(modelId) {
        let oldFormInfo;
        if (modelId) {
            const oldFormKey = this.activeForm.website_form_key;
            if (oldFormKey) {
                oldFormInfo = FormEditorRegistry.get(oldFormKey, null);
            }
            this.$target.find('.s_website_form_field').remove();
            this.activeForm = this.models.find(model => model.id === modelId);
            currentActionName = this.activeForm.website_form_label;
        }
        const formKey = this.activeForm.website_form_key;
        const formInfo = FormEditorRegistry.get(formKey, null);
        // Success page
        if (!this.$target[0].dataset.successMode) {
            this.$target[0].dataset.successMode = 'redirect';
        }
        if (this.$target[0].dataset.successMode === 'redirect') {
            const currentSuccessPage = this.$target[0].dataset.successPage;
            if (formInfo && formInfo.successPage) {
                this.$target[0].dataset.successPage = formInfo.successPage;
            } else if (!oldFormInfo || (oldFormInfo !== formInfo && oldFormInfo.successPage && currentSuccessPage === oldFormInfo.successPage)) {
                this.$target[0].dataset.successPage = '/contactus-thank-you';
            }
        }
        // Model name
        this.$target[0].dataset.model_name = this.activeForm.model;
        // Load template
        if (formInfo) {
            const formatInfo = this._getDefaultFormat();
            await formInfo.formFields.forEach(async field => {
                field.formatInfo = formatInfo;
                await this._fetchFieldRecords(field);
                this.$target.find('.s_website_form_submit, .s_website_form_recaptcha').first().before(this._renderField(field));
            });
            await this._fetchFormInfoFields(formInfo);
            this.renderContext.formInfo = formInfo;
        }
    }
    /**
     * Ensures formInfo fields are fetched.
     *
     * @private
     */
    async _fetchFormInfoFields(formInfo) {
        if (formInfo.fields) {
            const proms = formInfo.fields.map(field => this._fetchFieldRecords(field));
            await Promise.all(proms);
        }
    }
    /**
     * @override
     */
    async _getRenderContext() {
        const formKey = this.activeForm.website_form_key;
        const formInfo = FormEditorRegistry.get(formKey, null);
        await this._fetchFormInfoFields(formInfo);
        return {
            hasRecaptchaKey: !!session.recaptcha_public_key,
            modelCantChange: this.modelCantChange,
            models: this.models,
            formInfo: formInfo,
        };
    }
    /**
     * Set the correct mark on all fields.
     *
     * @private
     */
    _setLabelsMark() {
        this.$target[0].querySelectorAll('.s_website_form_mark').forEach(el => el.remove());
        const mark = this._getMark();
        if (!mark) {
            return;
        }
        let fieldsToMark = [];
        const requiredSelector = '.s_website_form_model_required, .s_website_form_required';
        const fields = Array.from(this.$target[0].querySelectorAll('.s_website_form_field'));
        if (this._isRequiredMark()) {
            fieldsToMark = fields.filter(el => el.matches(requiredSelector));
        } else if (this._isOptionalMark()) {
            fieldsToMark = fields.filter(el => !el.matches(requiredSelector));
        }
        fieldsToMark.forEach(field => {
            let span = document.createElement('span');
            span.classList.add('s_website_form_mark');
            span.textContent = ` ${mark}`;
            field.querySelector('.s_website_form_label').appendChild(span);
        });
    }
    /**
     * Redirects the user to the page of a specified action.
     *
     * @private
     * @param {string} action
     */
    _redirectToAction(action) {
        window.location.replace(`/web#action=${encodeURIComponent(action)}`);
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onToggleEndMessageClick() {
        this.showEndMessage = !this.showEndMessage;
        this.updateUIEndMessage();
        this.env.activateSnippet(this.showEndMessage ? this.$message : this.$target);
    }
}

export class WebsiteFieldEditor extends FieldEditor {
    /**
     * @override
     */
    async start() {
        // Build the custom select
        const select = this._getSelect();
        if (select) {
            const field = this._getActiveField();
            await this._replaceField(field);
        }
        return super.start(...arguments);
    }
    /**
     * @override
     */
    async updateUI() {
        if (this.rerender) {
            this.rerender = false;
            await this._updateRenderContext();
        }
        await super.updateUI(...arguments);
    }
    onFocus() {
        // Other fields type might have change to an existing type.
        // We need to reload the existing type list.
        this.rerender = true;
    }
    /**
     * Rerenders the clone to avoid id duplicates.
     *
     * @override
     */
    onClone() {
        const field = this._getActiveField();
        delete field.id;
        const fieldEl = this._renderField(field);
        this._replaceFieldElement(fieldEl);
    }
    /**
     * Removes the visibility conditions concerned by the deleted field
     *
     * @override
     */
    onRemove() {
        const fieldName = this.$target[0].querySelector('.s_website_form_input').name;
        const isMultipleField = this.formEl.querySelectorAll(`.s_website_form_input[name="${CSS.escape(fieldName)}"]`).length > 1;
        if (isMultipleField) {
            return;
        }
        const dependentFieldContainerEl = this.formEl.querySelectorAll(`[data-visibility-dependency="${CSS.escape(fieldName)}"]`);
        for (const fieldContainerEl of dependentFieldContainerEl) {
            this._deleteConditionalVisibility(fieldContainerEl);
        }
    }

    //----------------------------------------------------------------------
    // Options
    //----------------------------------------------------------------------

    /**
     * Add/remove a description to the field input
     */
    async toggleDescription(previewMode, value, params) {
        const field = this._getActiveField();
        field.description = !!value; // Will be changed to default description in qweb
        await this._replaceField(field);
    }
    /**
     * Replace the current field with the custom field selected.
     */
    async customField(previewMode, value, params) {
        // Both custom Field and existingField are called when selecting an option
        // value is '' for the method that should not be called.
        if (!value) {
            return;
        }
        const oldLabelText = this.$target[0].querySelector('.s_website_form_label_content').textContent;
        const field = this._getCustomField(value, oldLabelText);
        this._setActiveProperties(field);
        await this._replaceField(field);
        this.rerender = true;
    }
    /**
     * Replace the current field with the existing field selected.
     */
    async existingField(previewMode, value, params) {
        // see customField
        if (!value) {
            return;
        }
        const field = Object.assign({}, this.fields[value]);
        this._setActiveProperties(field);
        await this._replaceField(field);
        this.rerender = true;
    }
    /**
     * Set the the selction type of existing fields (radio or dropdown).
     *
     * @see this.selectClass for parameters
     */
    async existingFieldSelectType(previewMode, value, params) {
        const field = this._getActiveField();
        field.type = value;
        await this._replaceField(field);
    }
    /**
     * Set the name of the field on the label
     */
    setLabelText(previewMode, value, params) {
        this.$target.find('.s_website_form_label_content').text(value);
        if (this._isFieldCustom()) {
            value = this._getQuotesEncodedName(value);
            const multiple = this.$target[0].querySelector('.s_website_form_multiple');
            if (multiple) {
                multiple.dataset.name = value;
            }
            const inputEls = this.$target[0].querySelectorAll('.s_website_form_input');
            const previousInputName = inputEls[0].name;
            inputEls.forEach(el => el.name = value);

            // Synchronize the fields whose visibility depends on this field
            const dependentEls = this.formEl.querySelectorAll(`.s_website_form_field[data-visibility-dependency="${CSS.escape(previousInputName)}"]`);
            for (const dependentEl of dependentEls) {
                if (!previewMode && this._findCircular(this.$target[0], dependentEl)) {
                    // For all the fields whose visibility depends on this
                    // field, check if the new name creates a circular
                    // dependency and remove the problematic conditional
                    // visibility if it is the case. E.g. a field (A) depends on
                    // another (B) and the user renames "B" by "A".
                    this._deleteConditionalVisibility(dependentEl);
                } else {
                    dependentEl.dataset.visibilityDependency = value;
                }
            }

            if (!previewMode) {
                // TODO: @owl-options is this still true ?
                // As the field label changed, the list of available visibility
                // dependencies needs to be updated in order to not propose a
                // field that would create a circular dependency.
                this.rerender = true;
            }
        }
    }
    /**
     * Replace the field with the same field having the label in a different position.
     */
    async selectLabelPosition(previewMode, value, params) {
        const field = this._getActiveField();
        field.formatInfo.labelPosition = value;
        await this._replaceField(field);
    }
    async selectType(previewMode, value, params) {
        const field = this._getActiveField();
        field.type = value;
        await this._replaceField(field);
    }
    /**
     * Select the textarea default value
     */
    selectTextareaValue(previewMode, value, params) {
        this.$target[0].textContent = value;
        this.$target[0].value = value;
    }
    /**
     * Select the date as value property and convert it to the right format
     */
    selectValueProperty(previewMode, value, params) {
        const [target] = this.$target;
        const field = target.closest(".s_website_form_date, .s_website_form_datetime");
        const format = field.matches(".s_website_form_date") ? formatDate : formatDateTime;
        target.value = value ? format(luxon.DateTime.fromSeconds(parseInt(value))) : "";
    }
    /**
     * Select the display of the multicheckbox field (vertical & horizontal)
     */
    multiCheckboxDisplay(previewMode, value, params) {
        const target = this._getMultipleInputs();
        target.querySelectorAll('.checkbox, .radio').forEach(el => {
            if (value === 'horizontal') {
                el.classList.add('col-lg-4', 'col-md-6');
            } else {
                el.classList.remove('col-lg-4', 'col-md-6');
            }
        });
        target.dataset.display = value;
    }
    /**
     * Set the field as required or not
     */
    toggleRequired(previewMode, value, params) {
        const isRequired = this.$target[0].classList.contains(params.activeValue);
        this.$target[0].classList.toggle(params.activeValue, !isRequired);
        this.$target[0].querySelectorAll('input, select, textarea').forEach(el => el.toggleAttribute('required', !isRequired));
        this.callbacks.notifyOptions({
            optionName: 'WebsiteFormEditor',
            name: 'field_mark',
        });
    }
    /**
     * Apply the we-list on the target and rebuild the input(s)
     */
    async renderListItems(previewMode, value, params) {
        const valueList = JSON.parse(value);

        // Synchronize the possible values with the fields whose visibility
        // depends on the current field
        const newValuesText = valueList.map(value => value.name);
        const inputEls = this.$target[0].querySelectorAll('.s_website_form_input, option');
        const inputName = this.$target[0].querySelector('.s_website_form_input').name;
        for (let i = 0; i < inputEls.length; i++) {
            const input = inputEls[i];
            if (newValuesText[i] && input.value && !newValuesText.includes(input.value)) {
                for (const dependentEl of this.formEl.querySelectorAll(
                        `[data-visibility-condition="${CSS.escape(input.value)}"][data-visibility-dependency="${CSS.escape(inputName)}"]`)) {
                    dependentEl.dataset.visibilityCondition = newValuesText[i];
                }
                break;
            }
        }

        const field = this._getActiveField(true);
        field.records = valueList;
        await this._replaceField(field);
        if (this.valueList) {
            this.valueList.newRecordId = this._isFieldCustom() ? this._getNewRecordId() : '';
        }
    }
    /**
     * Sets the visibility of the field.
     *
     * @see this.selectClass for parameters
     */
    setVisibility(previewMode, widgetValue, params) {
        if (widgetValue === 'conditional') {
            const widget = this.findWidget('hidden_condition_opt');
            const firstValue = widget.getMethodsParams('setVisibilityDependency').possibleValues.find(el => el !== '');
            if (firstValue) {
                // Set a default visibility dependency
                this._setVisibilityDependency(firstValue);
                return;
            }
            this.dialog.add(ConfirmationDialog, {
                body: _t("There is no field available for this option."),
            });
        }
        this._deleteConditionalVisibility(this.$target[0]);
    }
    /**
     * @see this.selectClass for parameters
     */
    setVisibilityDependency(previewMode, widgetValue, params) {
        this._setVisibilityDependency(widgetValue);
    }
    /**
     * @override
     */
    async selectDataAttribute(previewMode, widgetValue, params) {
        await super.selectDataAttribute(...arguments);
        if (params.attributeName === "maxFilesNumber") {
            const allowMultipleFiles = params.activeValue > 1;
            this.$target[0].toggleAttribute("multiple", allowMultipleFiles);
        }
    }

    //----------------------------------------------------------------------
    // Private
    //----------------------------------------------------------------------

    /**
     * @override
     */
    _computeWidgetState(methodName, params) {
        switch (methodName) {
            case 'toggleDescription': {
                const description = this.$target[0].querySelector('.s_website_form_field_description');
                return !!description;
            }
            case 'customField':
                return this._isFieldCustom() ? this._getFieldType() : '';
            case 'existingField':
                return this._isFieldCustom() ? '' : this._getFieldName();
            case 'setLabelText':
                return this.$target.find('.s_website_form_label_content').text();
            case 'selectLabelPosition':
                return this._getLabelPosition();
            case 'selectType':
            case "existingFieldSelectType":
                return this._getFieldType();
            case 'selectTextareaValue':
                return this.$target[0].textContent;
            case 'selectValueProperty':
                return this.$target[0].getAttribute('value') || '';
            case 'multiCheckboxDisplay': {
                const target = this._getMultipleInputs();
                return target ? target.dataset.display : '';
            }
            case 'toggleRequired':
                return this.$target[0].classList.contains(params.activeValue) ? params.activeValue : 'false';
            case 'renderListItems':
                return JSON.stringify(this._getListItems());
            case 'setVisibilityDependency':
                return this.$target[0].dataset.visibilityDependency || '';
        }
        return super._computeWidgetState(...arguments);
    }
    /**
     * @override
     */
    _computeWidgetVisibility(widgetName, params) {
        const dependencyEl = this._getDependencyEl();
        switch (widgetName) {
            case 'hidden_condition_time_comparators_opt':
                return dependencyEl?.classList.contains("datetimepicker-input");
            case 'hidden_condition_date_between':
                return dependencyEl?.closest(".s_website_form_date")
                && ['between', '!between'].includes(this.$target[0].getAttribute('data-visibility-comparator'));
            case 'hidden_condition_datetime_between':
                return dependencyEl?.closest(".s_website_form_datetime")
                && ['between', '!between'].includes(this.$target[0].dataset.visibilityComparator);
            case 'hidden_condition_additional_datetime':
                return dependencyEl?.closest(".s_website_form_datetime")
                && !['set', '!set'].includes(this.$target[0].dataset.visibilityComparator);
            case 'hidden_condition_additional_date':
                return dependencyEl && dependencyEl?.closest(".s_website_form_date")
                && !['set', '!set'].includes(this.$target[0].dataset.visibilityComparator);
            case 'hidden_condition_additional_text':
                if (!this.$target[0].classList.contains('s_website_form_field_hidden_if') ||
                (dependencyEl && (['checkbox', 'radio'].includes(dependencyEl.type) || dependencyEl.nodeName === 'SELECT'))) {
                    return false;
                }
                if (!dependencyEl) {
                    return true;
                }
                if (dependencyEl?.classList.contains("datetimepicker-input")) {
                    return false;
                }
                return (['text', 'email', 'tel', 'url', 'search', 'password', 'number'].includes(dependencyEl.type)
                    || dependencyEl.nodeName === 'TEXTAREA') && !['set', '!set'].includes(this.$target[0].dataset.visibilityComparator);
            case 'hidden_condition_no_text_opt':
                return dependencyEl && (dependencyEl.type === 'checkbox' || dependencyEl.type === 'radio' || dependencyEl.nodeName === 'SELECT');
            case 'hidden_condition_num_opt':
                return dependencyEl && dependencyEl.type === 'number';
            case 'hidden_condition_text_opt':
                if (!this.$target[0].classList.contains('s_website_form_field_hidden_if') ||
                (dependencyEl?.classList.contains("datetimepicker-input"))) {
                    return false;
                }
                return !dependencyEl || (['text', 'email', 'tel', 'url', 'search', 'password'].includes(dependencyEl.type) ||
                dependencyEl.nodeName === 'TEXTAREA');
            case 'hidden_condition_date_opt':
                return dependencyEl?.closest(".s_website_form_date");
            case 'hidden_condition_datetime_opt':
                return dependencyEl?.closest(".s_website_form_datetime");
            case 'hidden_condition_file_opt':
                return dependencyEl && dependencyEl.type === 'file';
            case 'hidden_condition_opt':
                return this.$target[0].classList.contains('s_website_form_field_hidden_if');
            case 'char_input_type_opt':
                return !this.$target[0].classList.contains('s_website_form_custom') &&
                    ['char', 'email', 'tel', 'url'].includes(this.$target[0].dataset.type) &&
                    !this.$target[0].classList.contains('s_website_form_model_required');
            case "existing_field_select_type_opt":
                return !this._isFieldCustom() &&
                        ["selection", "many2one"].includes(this.$target[0].dataset.type);
            case 'multi_check_display_opt':
                return !!this._getMultipleInputs();
            case 'required_opt':
            case 'hidden_opt':
            case 'type_opt':
                return !this.$target[0].classList.contains('s_website_form_model_required');
            case "max_files_number_opt": {
                // Do not display the option if only one file is supposed to be
                // uploaded in the field.
                const fieldEl = this.$target[0].closest(".s_website_form_field");
                return fieldEl.classList.contains("s_website_form_custom") ||
                    ["one2many", "many2many"].includes(fieldEl.dataset.type);
            }
        }
        return super._computeWidgetVisibility(...arguments);
    }
    /**
     * Deletes all attributes related to conditional visibility.
     *
     * @param {HTMLElement} fieldEl
     */
     _deleteConditionalVisibility(fieldEl) {
        for (const name of FieldEditor.VISIBILITY_DATASET) {
            delete fieldEl.dataset[name];
        }
        fieldEl.classList.remove('s_website_form_field_hidden_if', 'd-none');
    }
    /**
     * @param {HTMLElement} [fieldEl]
     * @returns {HTMLElement} The visibility dependency of the field
     */
    _getDependencyEl(fieldEl = this.$target[0]) {
        const dependencyName = fieldEl.dataset.visibilityDependency;
        return this.formEl.querySelector(`.s_website_form_input[name="${CSS.escape(dependencyName)}"]`);
    }
    /**
     * @param {HTMLElement} dependentFieldEl
     * @param {HTMLElement} targetFieldEl
     * @returns {boolean} "true" if adding "dependentFieldEl" or any other field
     * with the same label in the conditional visibility of "targetFieldEl"
     * would create a circular dependency involving "targetFieldEl".
     */
    _findCircular(dependentFieldEl, targetFieldEl = this.$target[0]) {
        // Keep a register of the already visited fields to not enter an
        // infinite check loop.
        const visitedFields = new Set();
        const recursiveFindCircular = (dependentFieldEl, targetFieldEl) => {
            const dependentFieldName = this._getFieldName(dependentFieldEl);
            // Get all the fields that have the same label as the dependent
            // field.
            let dependentFieldEls = Array.from(this.formEl
                .querySelectorAll(`.s_website_form_input[name="${CSS.escape(dependentFieldName)}"]`))
                .map((el) => el.closest(".s_website_form_field"));
            // Remove the duplicated fields. This could happen if the field has
            // multiple inputs ("Multiple Checkboxes" for example.)
            dependentFieldEls = new Set(dependentFieldEls);
            const fieldName = this._getFieldName(targetFieldEl);
            for (const dependentFieldEl of dependentFieldEls) {
                // Only check for circular dependencies on fields that do not
                // already have been checked.
                if (!(visitedFields.has(dependentFieldEl))) {
                    // Add the dependentFieldEl in the set of checked field.
                    visitedFields.add(dependentFieldEl);
                    if (dependentFieldEl.dataset.visibilityDependency === fieldName) {
                        return true;
                    }
                    const dependencyInputEl = this._getDependencyEl(dependentFieldEl);
                    if (dependencyInputEl && recursiveFindCircular(dependencyInputEl.closest(".s_website_form_field"), targetFieldEl)) {
                        return true;
                    }
                }
            }
            return false;
        };
        return recursiveFindCircular(dependentFieldEl, targetFieldEl);
    }
    /**
     * @override
     */
    async _getRenderContext() {
        await this._loadRenderContextData();
        return {
            existingField: this.existingField,
            availableFields: this.availableFields,
            valueList: this.valueList,
            conditionInputs: this.conditionInputs,
            conditionValueList: this.conditionValueList,
        };
    }
    /**
     * @override
     */
    async _updateRenderContext() {
        Object.assign(this.renderContext, await this._getRenderContext());
    }
    /**
     * Loads render context data
     */
    async _loadRenderContextData() {
        // Get the authorized existing fields for the form model
        // Do it on each render because of custom property fields which can
        // change depending on the project selected.
        this.existingFields = await authorizedFieldsCache.get(this.formEl, this.env.services.orm).then((fields) => {
            this.fields = {};
            for (const [fieldName, field] of Object.entries(fields)) {
                field.name = fieldName;
                const fieldDomain = _getDomain(this.formEl, field.name, field.type, field.relation);
                field.domain = fieldDomain || field.domain || [];
                this.fields[fieldName] = field;
            }
            return Object.keys(fields).map(key => {
                const field = fields[key];
                return {
                    name: field.name,
                    string: field.string,
                };
            }).sort((a, b) => a.string.localeCompare(b.string, undefined, { numeric: true, sensitivity: "base" }));
        });
        // Update available visibility dependencies
        const existingDependencyNames = [];
        this.conditionInputs = [];
        for (const el of this.formEl.querySelectorAll('.s_website_form_field:not(.s_website_form_dnone)')) {
            const inputEl = el.querySelector('.s_website_form_input');
            if (el.querySelector('.s_website_form_label_content') && inputEl && inputEl.name
                    && inputEl.name !== this.$target[0].querySelector('.s_website_form_input').name
                    && !existingDependencyNames.includes(inputEl.name) && !this._findCircular(el)) {
                this.conditionInputs.push({
                    name: inputEl.name,
                    textContent: el.querySelector('.s_website_form_label_content').textContent,
                });
                existingDependencyNames.push(inputEl.name);
            }
        }

        const comparator = this.$target[0].dataset.visibilityComparator;
        const dependencyEl = this._getDependencyEl();
        if (dependencyEl) {
            if ((['radio', 'checkbox'].includes(dependencyEl.type) || dependencyEl.nodeName === 'SELECT')) {
                // Update available visibility options
                this.conditionValueList = [];
                const inputContainerEl = this.$target[0];
                if (dependencyEl.nodeName === 'SELECT') {
                    for (const option of dependencyEl.querySelectorAll('option')) {
                        this.conditionValueList.push({
                            value: option.value,
                            textContent: option.textContent || `<${_t("no value")}>`,
                        });
                    }
                    if (!inputContainerEl.dataset.visibilityCondition) {
                        inputContainerEl.dataset.visibilityCondition = dependencyEl.querySelector('option').value;
                    }
                } else { // DependencyEl is a radio or a checkbox
                    const dependencyContainerEl = dependencyEl.closest('.s_website_form_field');
                    const inputsInDependencyContainer = dependencyContainerEl.querySelectorAll('.s_website_form_input');
                    // TODO: @owl-options already wrong in master for e.g. Project/Tags
                    for (const el of inputsInDependencyContainer) {
                        this.conditionValueList.push({
                            value: el.value,
                            textContent: el.value,
                        });
                    }
                    if (!inputContainerEl.dataset.visibilityCondition) {
                        inputContainerEl.dataset.visibilityCondition = inputsInDependencyContainer[0].value;
                    }
                }
                if (!inputContainerEl.dataset.visibilityComparator) {
                    inputContainerEl.dataset.visibilityComparator = 'selected';
                }
            }
            if (!comparator) {
                // Set a default comparator according to the type of dependency
                if (dependencyEl.dataset.target) {
                    this.$target[0].dataset.visibilityComparator = 'after';
                } else if (['text', 'email', 'tel', 'url', 'search', 'password', 'number'].includes(dependencyEl.type)
                        || dependencyEl.nodeName === 'TEXTAREA') {
                    this.$target[0].dataset.visibilityComparator = 'equal';
                } else if (dependencyEl.type === 'file') {
                    this.$target[0].dataset.visibilityComparator = 'fileSet';
                }
            }
        }

        const currentFieldName = this._getFieldName();
        const fieldsInForm = Array.from(this.formEl.querySelectorAll('.s_website_form_field:not(.s_website_form_custom) .s_website_form_input')).map(el => el.name).filter(el => el !== currentFieldName);
        this.availableFields = this.existingFields.filter(field => !fieldsInForm.includes(field.name));

        const select = this._getSelect();
        const multipleInputs = this._getMultipleInputs();
        if (!select && !multipleInputs) {
            this.valueList = undefined;
            return;
        }

        const field = Object.assign({}, this.fields[this._getFieldName()]);
        const type = this._getFieldType();

        const optionText = select ? 'Option' : type === 'selection' ? 'Radio' : 'Checkbox';
        const defaults = [...this.$target[0].querySelectorAll('[checked], [selected]')].map(el => {
            return /^-?[0-9]{1,15}$/.test(el.value) ? parseInt(el.value) : el.value;
        });
        let availableRecords = undefined;
        if (!this._isFieldCustom()) {
            await this._fetchFieldRecords(field);
            availableRecords = JSON.stringify(field.records);
        }
        this.valueList = reactive({
            title: `${optionText} List`,
            addItemTitle: _t("Add new %s", optionText),
            hasDefault: ['one2many', 'many2many'].includes(type) ? 'multiple' : 'unique',
            defaults: JSON.stringify(defaults),
            availableRecords: availableRecords,
            newRecordId: this._isFieldCustom() ? this._getNewRecordId() : '',
        });
    }
    /**
     * Replaces the target content with the field provided.
     *
     * @private
     * @param {Object} field
     * @returns {Promise}
     */
    async _replaceField(field) {
        await this._fetchFieldRecords(field);
        const activeField = this._getActiveField();
        if (activeField.type !== field.type) {
            field.value = '';
        }
        const targetEl = this.$target[0].querySelector(".s_website_form_input");
        if (targetEl) {
            if (["checkbox", "radio"].includes(targetEl.getAttribute("type"))) {
                // Remove first checkbox/radio's id's final '0'.
                field.id = targetEl.id.slice(0, -1);
            } else {
                field.id = targetEl.id;
            }
        }
        const fieldEl = this._renderField(field);
        this._replaceFieldElement(fieldEl);
    }
    /**
     * Replaces the target with provided field.
     *
     * @private
     * @param {HTMLElement} fieldEl
     */
    _replaceFieldElement(fieldEl) {
        const inputEl = this.$target[0].querySelector('input');
        const dataFillWith = inputEl ? inputEl.dataset.fillWith : undefined;
        const hasConditionalVisibility = this.$target[0].classList.contains('s_website_form_field_hidden_if');
        const previousInputEl = this.$target[0].querySelector('.s_website_form_input');
        const previousName = previousInputEl.name;
        const previousType = previousInputEl.type;
        [...this.$target[0].childNodes].forEach(node => node.remove());
        [...fieldEl.childNodes].forEach(node => this.$target[0].appendChild(node));
        [...fieldEl.attributes].forEach(el => this.$target[0].removeAttribute(el.nodeName));
        [...fieldEl.attributes].forEach(el => this.$target[0].setAttribute(el.nodeName, el.nodeValue));
        if (hasConditionalVisibility) {
            this.$target[0].classList.add('s_website_form_field_hidden_if', 'd-none');
        }
        const dependentFieldEls = this.formEl.querySelectorAll(`.s_website_form_field[data-visibility-dependency="${CSS.escape(previousName)}"]`);
        const newFormInputEl = this.$target[0].querySelector('.s_website_form_input');
        const newName = newFormInputEl.name;
        const newType = newFormInputEl.type;
        if ((previousName !== newName || previousType !== newType) && dependentFieldEls) {
            // In order to keep the visibility conditions consistent,
            // when the name has changed, it means that the type has changed so
            // all fields whose visibility depends on this field must be updated so that
            // they no longer have conditional visibility
            for (const fieldEl of dependentFieldEls) {
                this._deleteConditionalVisibility(fieldEl);
            }
        }
        const newInputEl = this.$target[0].querySelector('input');
        if (newInputEl) {
            newInputEl.dataset.fillWith = dataFillWith;
        }
    }
    /**
     * Sets the visibility dependency of the field.
     *
     * @param {string} value name of the dependency input
     */
    _setVisibilityDependency(value) {
        delete this.$target[0].dataset.visibilityCondition;
        delete this.$target[0].dataset.visibilityComparator;
        // TODO: @owl-options somehow does not re-trigger the rendering
        this.rerender = true;
        this.$target[0].dataset.visibilityDependency = value;
    }
    /**
     * @private
     */
    _getListItems() {
        const select = this._getSelect();
        const multipleInputs = this._getMultipleInputs();
        let options = [];
        if (select) {
            options = [...select.querySelectorAll('option')];
        } else if (multipleInputs) {
            options = [...multipleInputs.querySelectorAll('.checkbox input, .radio input')];
        }
        const isFieldCustom = this._isFieldCustom();
        return options.map(opt => {
            const name = select ? opt : opt.nextElementSibling;
            return {
                id: isFieldCustom ? opt.id : /^-?[0-9]{1,15}$/.test(opt.value) ? parseInt(opt.value) : opt.value,
                display_name: name.textContent.trim(),
                selected: select ? opt.selected : opt.checked,
            };
        });
    }
    /**
     * Returns the next new record id.
     */
    _getNewRecordId() {
        const select = this._getSelect();
        const multipleInputs = this._getMultipleInputs();
        let options = [];
        if (select) {
            options = [...select.querySelectorAll('option')];
        } else if (multipleInputs) {
            options = [...multipleInputs.querySelectorAll('.checkbox input, .radio input')];
        }
        // TODO: @owl-option factorize code above
        const targetEl = this.$target[0].querySelector(".s_website_form_input");
        let id;
        if (["checkbox", "radio"].includes(targetEl.getAttribute("type"))) {
            // Remove first checkbox/radio's id's final '0'.
            id = targetEl.id.slice(0, -1);
        } else {
            id = targetEl.id;
        }
        return id + options.length;
    }
    /**
     * Returns the select element if it exist else null
     *
     * @private
     * @returns {HTMLElement}
     */
    _getSelect() {
        return this.$target[0].querySelector('select');
    }
}

export class AddFieldForm extends FormEditor {
    static isTopOption = true;
    static isTopFirstOption = true;

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Add a char field at the end of the form.
     * New field is set as active
     */
    async addField(previewMode, value, params) {
        const field = this._getCustomField('char', 'Custom Text');
        field.formatInfo = this._getDefaultFormat();
        const fieldEl = this._renderField(field);
        this.$target.find('.s_website_form_submit, .s_website_form_recaptcha').first().before(fieldEl);
        this.env.activateSnippet($(fieldEl));
    }
}

export class AddField extends FieldEditor {
    static isTopOption = true;
    static isTopFirstOption = true;

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Add a char field with active field properties after the active field.
     * New field is set as active
     */
    async addField(previewMode, value, params) {
        this.callbacks.notifyOptions({
            optionName: 'WebsiteFormEditor',
            name: 'add_field',
            data: {
                formatInfo: this._getFieldFormat(),
                $target: this.$target,
            },
        });
    }
}

// Superclass for options that need to disable a button from the snippet overlay
export class DisableOverlayButtonOption extends SnippetOption {
    // Disable a button of the snippet overlay
    disableButton(buttonName, message) {
        // TODO refactor in master
        const className = 'oe_snippet_' + buttonName;
        this.$overlay.add(this.$overlay.data('$optionsSection')).on('click', '.' + className, this.preventButton);
        const $buttons = this.$overlay.add(this.$overlay.data('$optionsSection')).find('.' + className);
        for (const buttonEl of $buttons) {
            // For a disabled element to display a tooltip, it must be wrapped
            // into a non-disabled element which holds the tooltip.
            buttonEl.classList.add('o_disabled');
            const spanEl = buttonEl.ownerDocument.createElement('span');
            spanEl.setAttribute('tabindex', 0);
            spanEl.setAttribute('title', message);
            buttonEl.replaceWith(spanEl);
            spanEl.appendChild(buttonEl);
            Tooltip.getOrCreateInstance(spanEl, {delay: 0});
        }
    }

    preventButton(event) {
        // Snippet options bind their functions before the editor, so we
        // can't cleanly unbind the editor onRemove function from here
        event.preventDefault();
        event.stopImmediatePropagation();
    }
}

// Disable duplicate button for model fields
export class WebsiteFormFieldModel extends DisableOverlayButtonOption {
    start() {
        this.disableButton('clone', _t('You cannot duplicate this field.'));
        return super.start(...arguments);
    }
}

// Disable delete button for model required fields
export class WebsiteFormFieldRequired extends DisableOverlayButtonOption {
    async willStart() {
        this.disableButton("remove", _t(
            "This field is mandatory for this action. You cannot remove it. Try hiding it with the"
            + " 'Visibility' option instead and add it a default value."
        ));
        await super.willStart(...arguments);
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async _getRenderContext() {
        const renderContext = await super._getRenderContext();
        if (currentActionName) {
            const fieldName = this.$target[0]
                .querySelector("input.s_website_form_input").getAttribute("name");
            renderContext.alertText = _t("The field “%(field)s” is mandatory for the action “%(action)s”.", {
                field: fieldName,
                action: currentActionName,
            });
        }
        return renderContext;
    }
}

// Disable delete and duplicate button for submit
export class WebsiteFormSubmitRequired extends DisableOverlayButtonOption {
    start() {
        this.disableButton('remove', _t('You can\'t remove the submit button of the form'));
        this.disableButton('clone', _t('You can\'t duplicate the submit button of the form.'));
        return super.start(...arguments);
    }
}

// Disable "Shown on Mobile/Desktop" option if for an hidden field
// TODO: @owl-options adapt when DeviceVisibility is converted
/*
options.registry.DeviceVisibility.include({

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     * /
    async _computeVisibility() {
        // Same as default but overridden by other apps
        return await super.computeVisibility(...arguments)
            && !this.$target.hasClass('s_website_form_field_hidden');
    },
});
*/

registerWebsiteOption("WebsiteFormEditor", {
    Class: WebsiteFormEditor,
    template: "website.s_website_form_form_option",
    selector: ".s_website_form",
    target: "form",
}, { sequence: 10 });
registerContentAdditionSelector(".s_website_form");

registerWebsiteOption("AddFieldForm", {
    Class: AddFieldForm,
    template: "website.s_website_form_add_field_form_option",
    selector: ".s_website_form",
    target: "form",
}, { sequence: 11 });

registerWebsiteOption("AddField", {
    Class: AddField,
    template: "website.s_website_form_add_field_option",
    selector: ".s_website_form_field",
    exclude: ".s_website_form_dnone",
}, { sequence: 12 });

registerWebsiteOption("WebsiteFormFieldRequired", {
    Class: WebsiteFormFieldRequired,
    template: "website.s_website_form_field_required_option",
    selector: ".s_website_form .s_website_form_model_required",
}, { sequence: 13 });

registerWebsiteOption("WebsiteFieldEditor", {
    Class: WebsiteFieldEditor,
    template: "website.s_website_form_field_option",
    selector: ".s_website_form_field",
    exclude: ".s_website_form_dnone",
    dropNear: ".s_website_form_field",
    dropLockWithin: "form",
}, { sequence: 14 });

registerWebsiteOption("WebsiteFormSubmitRequired", {
    Class: WebsiteFormSubmitRequired,
    template: "website.s_website_form_submit_option",
    selector: ".s_website_form_submit",
    exclude: ".s_website_form_no_submit_options",
}, { sequence: 15 });

/*
    TODO: @owl-options adapt when so_content_addition is "merged"
    <!-- Extend drop locations to columns -->
    <xpath expr="//t[@t-set='so_content_addition_selector']" position="inside">, .s_website_form</xpath>

    <xpath expr="//div" position="after">
        <!-- Remove the duplicate option of model fields -->
        <div data-js="WebsiteFormFieldModel" data-selector=".s_website_form .s_website_form_field:not(.s_website_form_custom)"/>

        <!-- Remove the delete and duplicate option of the submit button -->
        <div data-js="WebsiteFormSubmitRequired" data-selector=".s_website_form .s_website_form_submit"/>
    </xpath>

*/

export default {
    clearAllFormsInfo,
};
