odoo.define('website.form_editor', function (require) {
'use strict';

const core = require('web.core');
const FormEditorRegistry = require('website.form_editor_registry');
const options = require('web_editor.snippets.options');
const Dialog = require('web.Dialog');
const dom = require('web.dom');
require('website.editor.snippets.options');

const qweb = core.qweb;
const _t = core._t;

const FormEditor = options.Class.extend({
    xmlDependencies: [
        '/website/static/src/xml/website_form_editor.xml',
        '/google_recaptcha/static/src/xml/recaptcha.xml',
    ],

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
    _fetchFieldRecords: async function (field) {
        // Convert the required boolean to a value directly usable
        // in qweb js to avoid duplicating this in the templates
        field.required = field.required ? 1 : null;

        if (field.records) {
            return field.records;
        }
        // Set selection as records to avoid added conplexity
        if (field.type === 'selection') {
            field.records = field.selection.map(el => ({
                id: el[0],
                display_name: el[1],
            }));
        } else if (field.relation && field.relation !== 'ir.attachment') {
            field.records = await this._rpc({
                model: field.relation,
                method: 'search_read',
                args: [
                    field.domain,
                    ['display_name']
                ],
            });
        }
        return field.records;
    },
    /**
     * Generates a new ID.
     *
     * @private
     * @returns {string} The new ID
     */
    _generateUniqueID() {
        return `o${Math.random().toString(36).substring(2, 15)}`;
    },
    /**
     * Returns a field object
     *
     * @private
     * @param {string} type the type of the field
     * @param {string} name The name of the field used also as label
     * @returns {Object}
     */
    _getCustomField: function (type, name) {
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
    },
    /**
     * Returns the default formatInfos of a field.
     *
     * @private
     * @returns {Object}
     */
    _getDefaultFormat: function () {
        return {
            labelWidth: this.$target[0].querySelector('.s_website_form_label').style.width,
            labelPosition: 'left',
            multiPosition: 'horizontal',
            requiredMark: this._isRequiredMark(),
            optionalMark: this._isOptionalMark(),
            mark: this._getMark(),
        };
    },
    /**
     * @private
     * @returns {string}
     */
    _getMark: function () {
        return this.$target[0].dataset.mark;
    },
    /**
     * Replace all `"` character by `&quot;`, all `'` character by `&apos;` and
     * all "`" character by `&lsquo;`. This is needed in order to be able to
     * perform querySelector of this type: `querySelector(`[name="${name}"]`)`.
     * It also encodes the "\\" sequence to avoid having to escape it when doing
     * a `querySelector`.
     *
     * @param {string} name
     */
    _getQuotesEncodedName(name) {
        return name.replaceAll(/"/g, character => `&quot;`)
                   .replaceAll(/'/g, character => `&apos;`)
                   .replaceAll(/`/g, character => `&lsquo;`)
                   .replaceAll("\\", character => `&bsol;`);
    },
    /**
     * @private
     * @returns {boolean}
     */
    _isOptionalMark: function () {
        return this.$target[0].classList.contains('o_mark_optional');
    },
    /**
     * @private
     * @returns {boolean}
     */
    _isRequiredMark: function () {
        return this.$target[0].classList.contains('o_mark_required');
    },
    /**
     * @private
     * @param {Object} field
     * @returns {HTMLElement}
     */
    _renderField: function (field, resetId = false) {
        if (!field.id) {
            field.id = this._generateUniqueID();
        }
        const template = document.createElement('template');
        template.innerHTML = qweb.render("website.form_field_" + field.type, {field: field}).trim();
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
    },
});

const FieldEditor = FormEditor.extend({
    VISIBILITY_DATASET: ['visibilityDependency', 'visibilityCondition', 'visibilityComparator', 'visibilityBetween'],

    /**
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        this.formEl = this.$target[0].closest('form');
    },

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
    _getActiveField: function (noRecords) {
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
    },
    /**
     * Returns the format object of a field containing
     * the position, labelWidth and bootstrap col class
     *
     * @private
     * @returns {Object}
     */
    _getFieldFormat: function () {
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
    },
    /**
     * Returns the name of the field
     *
     * @private
     * @param {HTMLElement} fieldEl
     * @returns {string}
     */
    _getFieldName: function (fieldEl = this.$target[0]) {
        const multipleName = fieldEl.querySelector('.s_website_form_multiple');
        return multipleName ? multipleName.dataset.name : fieldEl.querySelector('.s_website_form_input').name;
    },
    /**
     * Returns the type of the  field, can be used for both custom and existing fields
     *
     * @private
     * @returns {string}
     */
    _getFieldType: function () {
        return this.$target[0].dataset.type;
    },
    /**
     * @private
     * @returns {string}
     */
    _getLabelPosition: function () {
        const label = this.$target[0].querySelector('.s_website_form_label');
        if (this.$target[0].querySelector('.row:not(.s_website_form_multiple)')) {
            return label.classList.contains('text-right') ? 'right' : 'left';
        } else {
            return label.classList.contains('d-none') ? 'none' : 'top';
        }
    },
    /**
     * Returns the multiple checkbox/radio element if it exist else null
     *
     * @private
     * @returns {HTMLElement}
     */
    _getMultipleInputs: function () {
        return this.$target[0].querySelector('.s_website_form_multiple');
    },
    /**
     * Returns true if the field is a custom field, false if it is an existing field
     *
     * @private
     * @returns {boolean}
     */
    _isFieldCustom: function () {
        return !!this.$target[0].classList.contains('s_website_form_custom');
    },
    /**
     * Returns true if the field is required by the model or by the user.
     *
     * @private
     * @returns {boolean}
     */
    _isFieldRequired: function () {
        const classList = this.$target[0].classList;
        return classList.contains('s_website_form_required') || classList.contains('s_website_form_model_required');
    },
    /**
     * Set the active field properties on the field Object
     *
     * @param {Object} field Field to complete with the active field info
     */
    _setActiveProperties(field) {
        const classList = this.$target[0].classList;
        const textarea = this.$target[0].querySelector('textarea');
        const input = this.$target[0].querySelector('input[type="text"], input[type="email"], input[type="number"], input[type="tel"], input[type="url"], textarea');
        const description = this.$target[0].querySelector('.s_website_form_field_description');
        field.placeholder = input && input.placeholder;
        if (input) {
            // textarea value has no attribute,  date/datetime timestamp property is formated
            field.value = input.getAttribute('value') || input.value;
        } else if (field.type === 'boolean') {
            field.value = !!this.$target[0].querySelector('input[type="checkbox"][checked]');
        }
        // property value is needed for date/datetime (formated date).
        field.propertyValue = input && input.value;
        field.description = description && description.outerHTML;
        field.rows = textarea && textarea.rows;
        field.required = classList.contains('s_website_form_required');
        field.modelRequired = classList.contains('s_website_form_model_required');
        field.hidden = classList.contains('s_website_form_field_hidden');
        field.formatInfo = this._getFieldFormat();
    },
});

options.registry.WebsiteFormEditor = FormEditor.extend({
    events: _.extend({}, options.Class.prototype.events || {}, {
        'click .toggle-edit-message': '_onToggleEndMessageClick',
    }),

    /**
     * @override
     */
    willStart: async function () {
        const _super = this._super.bind(this);

        // Hide change form parameters option for forms
        // e.g. User should not be enable to change existing job application form
        // to opportunity form in 'Apply job' page.
        this.modelCantChange = this.$target.attr('hide-change-model') !== undefined;
        if (this.modelCantChange) {
            return _super(...arguments);
        }

        // Get list of website_form compatible models.
        this.models = await this._rpc({
            model: 'ir.model',
            method: 'get_compatible_form_models',
        });

        const targetModelName = this.$target[0].dataset.model_name || 'mail.mail';
        this.activeForm = _.findWhere(this.models, {model: targetModelName});
        // Create the Form Action select
        this.selectActionEl = document.createElement('we-select');
        this.selectActionEl.setAttribute('string', 'Action');
        this.selectActionEl.dataset.noPreview = 'true';
        this.models.forEach(el => {
            const option = document.createElement('we-button');
            option.textContent = el.website_form_label;
            option.dataset.selectAction = el.id;
            this.selectActionEl.append(option);
        });

        return _super(...arguments);
    },
    /**
     * @override
     */
    start: function () {
        const proms = [this._super(...arguments)];
        // Disable text edition
        this.$target.attr('contentEditable', false);
        // Make button, description, and recaptcha editable
        this.$target.find('.s_website_form_send, .s_website_form_field_description, .s_website_form_recaptcha').attr('contentEditable', true);
        // Get potential message
        this.$message = this.$target.parent().find('.s_website_form_end_message');
        this.showEndMessage = false;
        // If the form has no model it means a new snippet has been dropped.
        // Apply the default model selected in willStart on it.
        if (!this.$target[0].dataset.model_name) {
            proms.push(this._applyFormModel());
        }
        return Promise.all(proms);
    },
    /**
     * @override
     */
    cleanForSave: function () {
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
                this._rpc({
                    model: 'ir.model.fields',
                    method: 'formbuilder_whitelist',
                    args: [model, _.uniq(fields)],
                });
            }
        }
        if (this.$message.length) {
            this.$target.removeClass('d-none');
            this.$message.addClass("d-none");
        }
    },
    /**
     * @override
     */
    updateUI: async function () {
        // If we want to rerender the xml we need to avoid the updateUI
        // as they are asynchronous and the ui might try to update while
        // we are building the UserValueWidgets.
        if (this.rerender) {
            this.rerender = false;
            await this._rerenderXML();
            return;
        }
        await this._super.apply(this, arguments);
        // End Message UI
        this.updateUIEndMessage();
    },
    /**
     * @see this.updateUI
     */
    updateUIEndMessage: function () {
        this.$target.toggleClass("d-none", this.showEndMessage);
        this.$message.toggleClass("d-none", !this.showEndMessage);
        this.$el.find(".toggle-edit-message").toggleClass('text-primary', this.showEndMessage);
    },
    /**
     * @override
     */
    notify: function (name, data) {
        this._super(...arguments);
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
            this.trigger_up('activate_snippet', {
                $snippet: $(fieldEl),
            });
        }
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Select the value of a field (hidden) that will be used on the model as a preset.
     * ie: The Job you apply for if the form is on that job's page.
     */
    addActionField: function (previewMode, value, params) {
        const fieldName = params.fieldName;
        if (params.isSelect === 'true') {
            value = parseInt(value);
        }
        this._addHiddenField(value, fieldName);
    },
    /**
     * Prompts the user to save changes before being redirected
     * towards an action specified in value.
     *
     * @see this.selectClass for parameters
     */
    promptSaveRedirect: function (name, value, widgetValue) {
        return new Promise((resolve, reject) => {
            const message = _t("Would you like to save before being redirected? Unsaved changes will be discarded.");
            Dialog.confirm(this, message, {
                cancel_callback: () => resolve(),
                buttons: [
                    {
                        text: _t("Save"),
                        classes: 'btn-primary',
                        click: (ev) => {
                            const restore = dom.addButtonLoadingEffect(ev.currentTarget);
                            this.trigger_up('request_save', {
                                reload: false,
                                onSuccess: () => {
                                    this._redirectToAction(value);
                                },
                                onFailure: () => {
                                    restore();
                                    this.displayNotification({
                                        message: _t("Something went wrong."),
                                        type: 'danger',
                                        sticky: true,
                                    });
                                    reject();
                                },
                            });
                            resolve();
                        },
                    }, {
                        text: _t("Discard"),
                        click: (ev) => {
                            dom.addButtonLoadingEffect(ev.currentTarget);
                            this._redirectToAction(value);
                        },
                    }, {
                        text: _t("Cancel"),
                        close: true,
                        click: () => resolve(),
                    },
                ],
            });
        });
    },
    /**
     * Changes the onSuccess event.
     */
    onSuccess: function (previewMode, value, params) {
        this.$target[0].dataset.successMode = value;
        if (value === 'message') {
            if (!this.$message.length) {
                this.$message = $(qweb.render('website.s_website_form_end_message'));
            }
            this.$target.after(this.$message);
        } else {
            this.showEndMessage = false;
            this.$message.remove();
        }
    },
    /**
     * Select the model to create with the form.
     */
    selectAction: async function (previewMode, value, params) {
        if (this.modelCantChange) {
            return;
        }
        await this._applyFormModel(parseInt(value));
        this.rerender = true;
    },
    /**
     * @override
     */
    selectClass: function (previewMode, value, params) {
        this._super(...arguments);
        if (params.name === 'field_mark_select') {
            this._setLabelsMark();
        }
    },
    /**
     * Set the mark string on the form
     */
    setMark: function (previewMode, value, params) {
        this.$target[0].dataset.mark = value.trim();
        this._setLabelsMark();
    },
    /**
     * Toggle the recaptcha legal terms
     */
    toggleRecaptchaLegal: function (previewMode, value, params) {
        const recaptchaLegalEl = this.$target[0].querySelector('.s_website_form_recaptcha');
        if (recaptchaLegalEl) {
            recaptchaLegalEl.remove();
        } else {
            const template = document.createElement('template');
            const labelWidth = this.$target[0].querySelector('.s_website_form_label').style.width;
            $(template).html(qweb.render("website.s_website_form_recaptcha_legal", {labelWidth: labelWidth}));
            const legal = template.content.firstElementChild;
            legal.setAttribute('contentEditable', true);
            this.$target.find('.s_website_form_submit').before(legal);
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _computeWidgetState: function (methodName, params) {
        switch (methodName) {
            case 'selectAction':
                return this.activeForm.id;
            case 'addActionField': {
                const value = this.$target.find(`.s_website_form_dnone input[name="${params.fieldName}"]`).val();
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
        return this._super(...arguments);
    },
    /**
     * @override
     */
    _renderCustomXML: function (uiFragment) {
        if (this.modelCantChange) {
            return;
        }
        // Add Action select
        const firstOption = uiFragment.childNodes[0];
        uiFragment.insertBefore(this.selectActionEl.cloneNode(true), firstOption);

        // Add Action related options
        const formKey = this.activeForm.website_form_key;
        const formInfo = FormEditorRegistry.get(formKey);
        if (!formInfo || !formInfo.fields) {
            return;
        }
        const proms = formInfo.fields.map(field => this._fetchFieldRecords(field));
        return Promise.all(proms).then(() => {
            formInfo.fields.forEach(field => {
                let option;
                switch (field.type) {
                    case 'many2one':
                        option = this._buildSelect(field);
                        break;
                    case 'char':
                        option = this._buildInput(field);
                        break;
                }
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
                uiFragment.insertBefore(option, firstOption);
            });
        });
    },
    /**
     * Add a hidden field to the form
     *
     * @private
     * @param {string} value
     * @param {string} fieldName
     */
    _addHiddenField: function (value, fieldName) {
        this.$target.find(`.s_website_form_dnone:has(input[name="${fieldName}"])`).remove();
        if (value) {
            const hiddenField = qweb.render('website.form_field_hidden', {
                field: {
                    name: fieldName,
                    value: value,
                },
            });
            this.$target.find('.s_website_form_submit').before(hiddenField);
        }
    },
    /**
     * Returns a we-input element from the field
     *
     * @private
     * @param {Object} field
     * @returns {HTMLElement}
     */
    _buildInput: function (field) {
        const inputEl = document.createElement('we-input');
        inputEl.dataset.noPreview = 'true';
        inputEl.dataset.fieldName = field.name;
        inputEl.dataset.addActionField = '';
        inputEl.setAttribute('string', field.string);
        inputEl.classList.add('o_we_large');
        return inputEl;
    },
    /**
     * Returns a we-select element with field's records as it's options
     *
     * @private
     * @param {Object} field
     * @return {HTMLElement}
     */
    _buildSelect: function (field) {
        const selectEl = document.createElement('we-select');
        selectEl.dataset.noPreview = 'true';
        selectEl.dataset.fieldName = field.name;
        selectEl.dataset.isSelect = 'true';
        selectEl.setAttribute('string', field.string);
        if (!field.required) {
            const noneButton = document.createElement('we-button');
            noneButton.textContent = 'None';
            noneButton.dataset.addActionField = 0;
            selectEl.append(noneButton);
        }
        field.records.forEach(el => {
            const button = document.createElement('we-button');
            button.textContent = el.display_name;
            button.dataset.addActionField = el.id;
            selectEl.append(button);
        });
        if (field.createAction) {
            return this._addCreateButton(selectEl, field.createAction);
        }
        return selectEl;
    },
    /**
     * Wraps an HTML element in a we-row element, and adds a
     * we-button linking to the given action.
     *
     * @private
     * @param {HTMLElement} element
     * @param {String} action
     * @returns {HTMLElement}
     */
    _addCreateButton: function (element, action) {
        const linkButtonEl = document.createElement('we-button');
        linkButtonEl.title = _t("Create new");
        linkButtonEl.dataset.noPreview = 'true';
        linkButtonEl.dataset.promptSaveRedirect = action;
        linkButtonEl.classList.add('fa', 'fa-fw', 'fa-plus');
        const projectRowEl = document.createElement('we-row');
        projectRowEl.append(element);
        projectRowEl.append(linkButtonEl);
        return projectRowEl;
    },
    /**
     * Apply the model on the form changing it's fields
     *
     * @private
     * @param {Integer} modelId
     */
    _applyFormModel: async function (modelId) {
        let oldFormInfo;
        if (modelId) {
            const oldFormKey = this.activeForm.website_form_key;
            if (oldFormKey) {
                oldFormInfo = FormEditorRegistry.get(oldFormKey);
            }
            this.$target.find('.s_website_form_field').remove();
            this.activeForm = _.findWhere(this.models, {id: modelId});
        }
        const formKey = this.activeForm.website_form_key;
        const formInfo = FormEditorRegistry.get(formKey);
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
        }
    },
    /**
     * Set the correct mark on all fields.
     *
     * @private
     */
    _setLabelsMark: function () {
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
    },
    /**
     * Redirects the user to the page of a specified action.
     *
     * @private
     * @param {string} action
     */
    _redirectToAction: function (action) {
        window.location.replace(`/web#action=${encodeURIComponent(action)}`);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onToggleEndMessageClick: function () {
        this.showEndMessage = !this.showEndMessage;
        this.updateUIEndMessage();
        this.trigger_up('activate_snippet', {
            $snippet: this.showEndMessage ? this.$message : this.$target,
        });
    },
});

const authorizedFieldsCache = {};

options.registry.WebsiteFieldEditor = FieldEditor.extend({
    /**
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        this.rerender = true;
    },
    /**
     * @override
     */
    willStart: async function () {
        const _super = this._super.bind(this);
        // Get the authorized existing fields for the form model
        const model = this.formEl.dataset.model_name;
        let getFields;
        if (model in authorizedFieldsCache) {
            getFields = authorizedFieldsCache[model];
        } else {
            getFields = this._rpc({
                model: "ir.model",
                method: "get_authorized_fields",
                args: [model],
            });
            authorizedFieldsCache[model] = getFields;
        }

        this.existingFields = await getFields.then(fields => {
            this.fields = _.each(fields, function (field, fieldName) {
                field.name = fieldName;
                field.domain = field.domain || [];
            });
            // Create the buttons for the type we-select
            return Object.keys(fields).map(key => {
                const field = fields[key];
                const button = document.createElement('we-button');
                button.textContent = field.string;
                button.dataset.existingField = field.name;
                return button;
            }).sort((a, b) => (a.textContent > b.textContent) ? 1 : (a.textContent < b.textContent) ? -1 : 0);
        });
        return _super(...arguments);
    },
    /**
     * @override
     */
    start: async function () {
        const _super = this._super.bind(this);
        // Build the custom select
        const select = this._getSelect();
        if (select) {
            const field = this._getActiveField();
            await this._replaceField(field);
        }
        return _super(...arguments);
    },
    /**
     * @override
     */
    cleanForSave: function () {
        this.$target[0].querySelectorAll('#editable_select').forEach(el => el.remove());
        const select = this._getSelect();
        if (select) {
            select.style.display = '';
        }
    },
    /**
     * @override
     */
    updateUI: async function () {
        // See Form updateUI
        if (this.rerender) {
            this.rerender = false;
            await this._rerenderXML();
            return;
        }
        await this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    onFocus: function () {
        // Other fields type might have change to an existing type.
        // We need to reload the existing type list.
        this.rerender = true;
    },
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
    },
    /**
     * Removes the visibility conditions concerned by the deleted field
     *
     * @override
     */
    onRemove() {
        const fieldName = this.$target[0].querySelector('.s_website_form_input').name;
        const isMultipleField = this.formEl.querySelectorAll(`.s_website_form_input[name="${fieldName}"]`).length > 1;
        if (isMultipleField) {
            return;
        }
        const dependentFieldContainerEl = this.formEl.querySelectorAll(`[data-visibility-dependency="${fieldName}"]`);
        for (const fieldContainerEl of dependentFieldContainerEl) {
            this._deleteConditionalVisibility(fieldContainerEl);
        }
    },

    //----------------------------------------------------------------------
    // Options
    //----------------------------------------------------------------------

    /**
     * Add/remove a description to the field input
     */
    toggleDescription: async function (previewMode, value, params) {
        const field = this._getActiveField();
        field.description = !!value; // Will be changed to default description in qweb
        await this._replaceField(field);
    },
    /**
     * Replace the current field with the custom field selected.
     */
    customField: async function (previewMode, value, params) {
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
    },
    /**
     * Replace the current field with the existing field selected.
     */
    existingField: async function (previewMode, value, params) {
        // see customField
        if (!value) {
            return;
        }
        const field = Object.assign({}, this.fields[value]);
        this._setActiveProperties(field);
        await this._replaceField(field);
        this.rerender = true;
    },
    /**
     * Set the name of the field on the label
     */
    setLabelText: function (previewMode, value, params) {
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
            const dependentEls = this.formEl.querySelectorAll(`.s_website_form_field[data-visibility-dependency="${previousInputName}"]`);
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
                // As the field label changed, the list of available visibility
                // dependencies needs to be updated in order to not propose a
                // field that would create a circular dependency.
                this.rerender = true;
            }
        }
    },
    /**
     * Replace the field with the same field having the label in a different position.
     */
    selectLabelPosition: async function (previewMode, value, params) {
        const field = this._getActiveField();
        field.formatInfo.labelPosition = value;
        await this._replaceField(field);
    },
    selectType: async function (previewMode, value, params) {
        const field = this._getActiveField();
        field.type = value;
        await this._replaceField(field);
    },
    /**
     * Select the textarea default value
     */
    selectTextareaValue: function (previewMode, value, params) {
        this.$target[0].textContent = value;
        this.$target[0].value = value;
    },
    /**
     * Select the date as value property and convert it to the right format
     */
    selectValueProperty: function (previewMode, value, params) {
        this.$target[0].value = value ? moment.unix(value).format(params.format) : '';
    },
    /**
     * Select the display of the multicheckbox field (vertical & horizontal)
     */
    multiCheckboxDisplay: function (previewMode, value, params) {
        const target = this._getMultipleInputs();
        target.querySelectorAll('.checkbox, .radio').forEach(el => {
            if (value === 'horizontal') {
                el.classList.add('col-lg-4', 'col-md-6');
            } else {
                el.classList.remove('col-lg-4', 'col-md-6');
            }
        });
        target.dataset.display = value;
    },
    /**
     * Set the field as required or not
     */
    toggleRequired: function (previewMode, value, params) {
        const isRequired = this.$target[0].classList.contains(params.activeValue);
        this.$target[0].classList.toggle(params.activeValue, !isRequired);
        this.$target[0].querySelectorAll('input, select, textarea').forEach(el => el.toggleAttribute('required', !isRequired));
        this.trigger_up('option_update', {
            optionName: 'WebsiteFormEditor',
            name: 'field_mark',
        });
    },
    /**
     * Apply the we-list on the target and rebuild the input(s)
     */
    renderListItems: async function (previewMode, value, params) {
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
                        `[data-visibility-condition="${input.value}"][data-visibility-dependency="${inputName}"]`)) {
                    dependentEl.dataset.visibilityCondition = newValuesText[i];
                }
                break;
            }
        }

        const field = this._getActiveField(true);
        field.records = valueList;
        await this._replaceField(field);
    },
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
            Dialog.confirm(this, _t("There is no field available for this option."));
        }
        this._deleteConditionalVisibility(this.$target[0]);
    },
    /**
     * @see this.selectClass for parameters
     */
    setVisibilityDependency(previewMode, widgetValue, params) {
        this._setVisibilityDependency(widgetValue);
    },

    //----------------------------------------------------------------------
    // Private
    //----------------------------------------------------------------------

    /**
     * @override
     */
    _computeWidgetState: function (methodName, params) {
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
        return this._super(...arguments);
    },
    /**
     * @override
     */
    _computeWidgetVisibility: function (widgetName, params) {
        const dependencyEl = this._getDependencyEl();
        switch (widgetName) {
            case 'hidden_condition_time_comparators_opt':
                return dependencyEl && dependencyEl.dataset.target;
            case 'hidden_condition_date_between':
                return dependencyEl && dependencyEl.dataset.target && dependencyEl.dataset.target.includes('#datepicker')
                && ['between', '!between'].includes(this.$target[0].getAttribute('data-visibility-comparator'));
            case 'hidden_condition_datetime_between':
                return dependencyEl && dependencyEl.dataset.target && dependencyEl.dataset.target.includes('#datetimepicker')
                && ['between', '!between'].includes(this.$target[0].dataset.visibilityComparator);
            case 'hidden_condition_additional_datetime':
                return dependencyEl && dependencyEl.dataset.target && dependencyEl.dataset.target.includes('#datetimepicker')
                && !['set', '!set'].includes(this.$target[0].dataset.visibilityComparator);
            case 'hidden_condition_additional_date':
                return dependencyEl && dependencyEl.dataset.target && dependencyEl.dataset.target.includes('#datepicker')
                && !['set', '!set'].includes(this.$target[0].dataset.visibilityComparator);
            case 'hidden_condition_additional_text':
                if (!this.$target[0].classList.contains('s_website_form_field_hidden_if') ||
                (dependencyEl && (['checkbox', 'radio'].includes(dependencyEl.type) || dependencyEl.nodeName === 'SELECT'))) {
                    return false;
                }
                if (!dependencyEl) {
                    return true;
                }
                if (dependencyEl.dataset.target && dependencyEl.dataset.target.includes('#date')) {
                    return false;
                }
                return (['text', 'email', 'tel', 'url', 'search', 'password', 'number'].includes(dependencyEl.type)
                    || dependencyEl.nodeName === 'TEXTAREA') && !['set', '!set'].includes(this.$target[0].dataset.visibilityComparator);
            case 'hidden_condition_no_text_opt':
                return dependencyEl && (dependencyEl.type === 'checkbox' || dependencyEl.type === 'radio' || dependencyEl.nodeName === 'SELECT');
            case 'hidden_condition_num_opt':
                return dependencyEl && dependencyEl.type === 'number';
            case 'hidden_condition_text_opt':
                if (!this.$target[0].classList.contains('s_website_form_field_hidden_if') || (dependencyEl &&
                dependencyEl.dataset.target && dependencyEl.dataset.target.includes('#date'))) {
                    return false;
                }
                return !dependencyEl || (['text', 'email', 'tel', 'url', 'search', 'password'].includes(dependencyEl.type) ||
                dependencyEl.nodeName === 'TEXTAREA');
            case 'hidden_condition_date_opt':
                return dependencyEl && dependencyEl.dataset.target && dependencyEl.dataset.target.includes('#datepicker');
            case 'hidden_condition_datetime_opt':
                return dependencyEl && dependencyEl.dataset.target && dependencyEl.dataset.target.includes('#datetimepicker');
            case 'hidden_condition_file_opt':
                return dependencyEl && dependencyEl.type === 'file';
            case 'hidden_condition_opt':
                return this.$target[0].classList.contains('s_website_form_field_hidden_if');
            case 'char_input_type_opt':
                return !this.$target[0].classList.contains('s_website_form_custom') && ['char', 'email', 'tel', 'url'].includes(this.$target[0].dataset.type);
            case 'multi_check_display_opt':
                return !!this._getMultipleInputs();
            case 'required_opt':
            case 'hidden_opt':
            case 'type_opt':
                return !this.$target[0].classList.contains('s_website_form_model_required');
        }
        return this._super(...arguments);
    },
    /**
     * Deletes all attributes related to conditional visibility.
     *
     * @param {HTMLElement} fieldEl
     */
     _deleteConditionalVisibility(fieldEl) {
        for (const name of this.VISIBILITY_DATASET) {
            delete fieldEl.dataset[name];
        }
        fieldEl.classList.remove('s_website_form_field_hidden_if', 'd-none');
    },
    /**
     * @param {HTMLElement} [fieldEl]
     * @returns {HTMLElement} The visibility dependency of the field
     */
    _getDependencyEl(fieldEl = this.$target[0]) {
        const dependencyName = fieldEl.dataset.visibilityDependency;
        return this.formEl.querySelector(`.s_website_form_input[name="${dependencyName}"]`);
    },
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
                .querySelectorAll(`.s_website_form_input[name="${dependentFieldName}"]`))
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
    },
    /**
     * @override
     */
    _renderCustomXML: async function (uiFragment) {
        // Create the file visibility selector.
        uiFragment.querySelector('we-row[data-name="hidden_condition_opt"]').append($(`
            <we-select data-name="hidden_condition_file_opt" data-attribute-name="visibilityComparator" data-no-preview="true">
                <we-button data-select-data-attribute="fileSet">${_t("Is set")}</we-button>
                <we-button data-select-data-attribute="!fileSet">${_t("Is not set")}</we-button>
            </we-select>
        `)[0]);

        // Update available visibility dependencies
        const selectDependencyEl = uiFragment.querySelector('we-select[data-name="hidden_condition_opt"]');
        if (selectDependencyEl) {
            const existingDependencyNames = [];
            for (const el of this.formEl.querySelectorAll('.s_website_form_field:not(.s_website_form_dnone)')) {
                const inputEl = el.querySelector('.s_website_form_input');
                if (el.querySelector('.s_website_form_label_content') && inputEl && inputEl.name
                        && inputEl.name !== this.$target[0].querySelector('.s_website_form_input').name
                        && !existingDependencyNames.includes(inputEl.name) && !this._findCircular(el)) {
                    const button = document.createElement('we-button');
                    button.textContent = el.querySelector('.s_website_form_label_content').textContent;
                    button.dataset.setVisibilityDependency = inputEl.name;
                    selectDependencyEl.append(button);
                    existingDependencyNames.push(inputEl.name);
                }
            }

            const comparator = this.$target[0].dataset.visibilityComparator;
            const dependencyEl = this._getDependencyEl();
            if (dependencyEl) {
                if ((['radio', 'checkbox'].includes(dependencyEl.type) || dependencyEl.nodeName === 'SELECT')) {
                    // Update available visibility options
                    const selectOptEl = uiFragment.querySelectorAll('we-select[data-name="hidden_condition_no_text_opt"]')[1];
                    const inputContainerEl = this.$target[0];
                    const dependencyEl = this._getDependencyEl();
                    if (dependencyEl.nodeName === 'SELECT') {
                        for (const option of dependencyEl.querySelectorAll('option')) {
                            const button = document.createElement('we-button');
                            button.textContent = option.value || `<${_t("no value")}>`;
                            button.dataset.selectDataAttribute = option.value;
                            selectOptEl.append(button);
                        }
                        if (!inputContainerEl.dataset.visibilityCondition) {
                            inputContainerEl.dataset.visibilityCondition = dependencyEl.querySelector('option').value;
                        }
                    } else { // DependecyEl is a radio or a checkbox
                        const dependencyContainerEl = dependencyEl.closest('.s_website_form_field');
                        const inputsInDependencyContainer = dependencyContainerEl.querySelectorAll('.s_website_form_input');
                        for (const el of inputsInDependencyContainer) {
                            const button = document.createElement('we-button');
                            button.textContent = el.value;
                            button.dataset.selectDataAttribute = el.value;
                            selectOptEl.append(button);
                        }
                        if (!inputContainerEl.dataset.visibilityCondition) {
                            inputContainerEl.dataset.visibilityCondition = inputsInDependencyContainer[0].value;
                        }
                    }
                    if (!inputContainerEl.dataset.visibilityComparator) {
                        inputContainerEl.dataset.visibilityComparator = 'selected';
                    }
                    this.rerender = comparator ? this.rerender : true;
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
        }

        const selectEl = uiFragment.querySelector('we-select[data-name="type_opt"]');
        const currentFieldName = this._getFieldName();
        const fieldsInForm = Array.from(this.formEl.querySelectorAll('.s_website_form_field:not(.s_website_form_custom) .s_website_form_input')).map(el => el.name).filter(el => el !== currentFieldName);
        const availableFields = this.existingFields.filter(el => !fieldsInForm.includes(el.dataset.existingField));
        if (availableFields.length) {
            const title = document.createElement('we-title');
            title.textContent = 'Existing fields';
            availableFields.unshift(title);
            availableFields.forEach(option => selectEl.append(option.cloneNode(true)));
        }

        const select = this._getSelect();
        const multipleInputs = this._getMultipleInputs();
        if (!select && !multipleInputs) {
            return;
        }

        const field = Object.assign({}, this.fields[this._getFieldName()]);
        const type = this._getFieldType();

        const list = document.createElement('we-list');
        const optionText = select ? 'Option' : type === 'selection' ? 'Radio' : 'Checkbox';
        list.setAttribute('string', `${optionText} List`);
        list.dataset.addItemTitle = _.str.sprintf(_t("Add new %s"), optionText);
        list.dataset.renderListItems = '';

        list.dataset.hasDefault = ['one2many', 'many2many'].includes(type) ? 'multiple' : 'unique';
        const defaults = [...this.$target[0].querySelectorAll('[checked], [selected]')].map(el => {
            return /^-?[0-9]{1,15}$/.test(el.value) ? parseInt(el.value) : el.value;
        });
        list.dataset.defaults = JSON.stringify(defaults);

        if (!this._isFieldCustom()) {
            await this._fetchFieldRecords(field);
            list.dataset.availableRecords = JSON.stringify(field.records);
        }
        if (selectDependencyEl) {
            uiFragment.insertBefore(list, uiFragment.querySelector('we-select[string="Visibility"]'));
        } else {
            uiFragment.appendChild(list);
        }
    },
    /**
     * Replaces the target content with the field provided.
     *
     * @private
     * @param {Object} field
     * @returns {Promise}
     */
    _replaceField: async function (field) {
        await this._fetchFieldRecords(field);
        const activeField = this._getActiveField();
        if (activeField.type !== field.type) {
            field.value = '';
        }
        const fieldEl = this._renderField(field);
        this._replaceFieldElement(fieldEl);
    },
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
        const previousName = this.$target[0].querySelector('.s_website_form_input').name;
        [...this.$target[0].childNodes].forEach(node => node.remove());
        [...fieldEl.childNodes].forEach(node => this.$target[0].appendChild(node));
        [...fieldEl.attributes].forEach(el => this.$target[0].removeAttribute(el.nodeName));
        [...fieldEl.attributes].forEach(el => this.$target[0].setAttribute(el.nodeName, el.nodeValue));
        if (hasConditionalVisibility) {
            this.$target[0].classList.add('s_website_form_field_hidden_if', 'd-none');
        }
        const dependentFieldEls = this.formEl.querySelectorAll(`.s_website_form_field[data-visibility-dependency="${previousName}"]`);
        const newName = this.$target[0].querySelector('.s_website_form_input').name;
        if (previousName !== newName && dependentFieldEls) {
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
    },
    /**
     * Sets the visibility dependency of the field.
     *
     * @param {string} value name of the dependency input
     */
     _setVisibilityDependency(value) {
        delete this.$target[0].dataset.visibilityCondition;
        delete this.$target[0].dataset.visibilityComparator;
        const previousDependency = this._getDependencyEl();
        if (this.formEl.querySelector(`.s_website_form_input[name="${value}"]`).type !== (previousDependency && previousDependency.type)) {
            this.rerender = true;
        }
        this.$target[0].dataset.visibilityDependency = value;
    },
    /**
     * @private
     */
    _getListItems: function () {
        const select = this._getSelect();
        const multipleInputs = this._getMultipleInputs();
        let options = [];
        if (select) {
            options = [...select.querySelectorAll('option')];
        } else if (multipleInputs) {
            options = [...multipleInputs.querySelectorAll('.checkbox input, .radio input')];
        }
        return options.map(opt => {
            const name = select ? opt : opt.nextElementSibling;
            return {
                id: /^-?[0-9]{1,15}$/.test(opt.value) ? parseInt(opt.value) : opt.value,
                display_name: name.textContent.trim(),
                selected: select ? opt.selected : opt.checked,
            };
        });
    },
    /**
     * Returns the select element if it exist else null
     *
     * @private
     * @returns {HTMLElement}
     */
    _getSelect: function () {
        return this.$target[0].querySelector('select');
    },
});

options.registry.AddFieldForm = FormEditor.extend({
    isTopOption: true,
    isTopFirstOption: true,

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Add a char field at the end of the form.
     * New field is set as active
     */
    addField: async function (previewMode, value, params) {
        const field = this._getCustomField('char', 'Custom Text');
        field.formatInfo = this._getDefaultFormat();
        const fieldEl = this._renderField(field);
        this.$target.find('.s_website_form_submit, .s_website_form_recaptcha').first().before(fieldEl);
        this.trigger_up('activate_snippet', {
            $snippet: $(fieldEl),
        });
    },
});

options.registry.AddField = FieldEditor.extend({
    isTopOption: true,
    isTopFirstOption: true,

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Add a char field with active field properties after the active field.
     * New field is set as active
     */
    addField: async function (previewMode, value, params) {
        this.trigger_up('option_update', {
            optionName: 'WebsiteFormEditor',
            name: 'add_field',
            data: {
                formatInfo: this._getFieldFormat(),
                $target: this.$target,
            },
        });
    },
});

// Superclass for options that need to disable a button from the snippet overlay
const DisableOverlayButtonOption = options.Class.extend({
    // Disable a button of the snippet overlay
    disableButton: function (buttonName, message) {
        // TODO refactor in master
        const className = 'oe_snippet_' + buttonName;
        this.$overlay.add(this.$overlay.data('$optionsSection')).on('click', '.' + className, this.preventButton);
        const $button = this.$overlay.add(this.$overlay.data('$optionsSection')).find('.' + className);
        $button.attr('title', message).tooltip({delay: 0});
        // TODO In master: add `o_disabled` but keep actual class.
        $button.removeClass(className); // Disable the functionnality
    },

    preventButton: function (event) {
        // Snippet options bind their functions before the editor, so we
        // can't cleanly unbind the editor onRemove function from here
        event.preventDefault();
        event.stopImmediatePropagation();
    }
});

// Disable duplicate button for model fields
options.registry.WebsiteFormFieldModel = DisableOverlayButtonOption.extend({
    start: function () {
        this.disableButton('clone', _t('You can\'t duplicate a model field.'));
        return this._super.apply(this, arguments);
    }
});

// Disable delete button for model required fields
options.registry.WebsiteFormFieldRequired = DisableOverlayButtonOption.extend({
    start: function () {
        this.disableButton('remove', _t('You can\'t remove a field that is required by the model itself.'));
        return this._super.apply(this, arguments);
    }
});

// Disable delete and duplicate button for submit
options.registry.WebsiteFormSubmitRequired = DisableOverlayButtonOption.extend({
    start: function () {
        this.disableButton('remove', _t('You can\'t remove the submit button of the form'));
        this.disableButton('clone', _t('You can\'t duplicate the submit button of the form.'));
        return this._super.apply(this, arguments);
    }
});

// Disable "Shown on Mobile" option if for an hidden field
options.registry.MobileVisibility.include({

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async _computeVisibility() {
        // Same as default but overridden by other apps
        return await this._super(...arguments)
            && !this.$target.hasClass('s_website_form_field_hidden');
    },
});
});
