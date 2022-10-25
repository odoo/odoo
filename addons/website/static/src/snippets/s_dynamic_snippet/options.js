odoo.define('website.s_dynamic_snippet_options', function (require) {
'use strict';

const options = require('web_editor.snippets.options');

const dynamicSnippetOptions = options.Class.extend({

    /**
     *
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        // specify model name in subclasses to filter the list of available model record filters
        this.modelNameFilter = undefined;
        this.contextualFilterDomain = [];
        this.dynamicFilters = {};
        // name of the model of the currently selected filter, used to fetch templates
        this.currentModelName = undefined;
        this.dynamicFilterTemplates = {};
        // Indicates that some current options are a default selection.
        this.isOptionDefault = {};
    },
    /**
     *
     * @override
     */
    onBuilt: function () {
        this._setOptionsDefaultValues();
        // TODO Remove in master: adapt dropped snippet template.
        if (this.$target[0].classList.contains('d-none') && !this.$target[0].classList.contains('d-md-block')) {
            // Remove the 'd-none' of the old template if it is not related to
            // the visible on mobile option.
            this.$target[0].classList.remove('d-none');
        }
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     *
     * @see this.selectClass for parameters
     */
    selectDataAttribute: function (previewMode, widgetValue, params) {
        this._super.apply(this, arguments);
        if (params.attributeName === 'filterId' && previewMode === false) {
            const filter = this.dynamicFilters[parseInt(widgetValue)];
            this.$target.get(0).dataset.numberOfRecords = filter.limit;
            this._filterUpdated(filter);
        }
        if (params.attributeName === 'templateKey' && previewMode === false) {
            this._templateUpdated(widgetValue, params.activeValue);
        }
        if (params.attributeName === 'numberOfRecords' && previewMode === false) {
            const dataSet = this.$target.get(0).dataset;
            const numberOfElements = parseInt(dataSet.numberOfElements);
            const numberOfRecords = parseInt(dataSet.numberOfRecords);
            const numberOfElementsSmallDevices = parseInt(dataSet.numberOfElementsSmallDevices);
            if (numberOfElements > numberOfRecords) {
                dataSet.numberOfElements = numberOfRecords;
            }
            if (numberOfElementsSmallDevices > numberOfRecords) {
                dataSet.numberOfElementsSmallDevices = numberOfRecords;
            }
        }
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * See from updateUI in s_website_form
     * 
     * @override
     */
    async updateUI() {
        if (this.rerender) {
            this.rerender = false;
            await this._rerenderXML();
            return;
        }
        await this._super(...arguments);
    },

    /**
     * @override
     */
    async updateUIVisibility() {
        await this._super(...arguments);
        const template = this._getCurrentTemplate();
        const groupingMessage = this.el.querySelector('.o_grouping_message');
        groupingMessage.classList.toggle('d-none', template && !!template.numOfEl && !!template.numOfElSm);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _getCurrentTemplate: function () {
        return this.dynamicFilterTemplates[this.$target.get(0).dataset['templateKey']];
    },

    _getTemplateClass: function (templateKey) {
        return templateKey.replace(/.*\.dynamic_filter_template_/, "s_");
    },

    /**
     *
     * @override
     * @private
     */
    _computeWidgetVisibility: function (widgetName, params) {
        if (widgetName === 'filter_opt') {
            // Hide if exaclty one is available: show when none to help understand what is missing
            return Object.keys(this.dynamicFilters).length !== 1;
        }

        if (widgetName === 'number_of_elements_opt') {
            const template = this._getCurrentTemplate();
            return template && !template.numOfEl;
        }

        if (widgetName === 'number_of_elements_small_devices_opt') {
            const template = this._getCurrentTemplate();
            return template && !template.numOfElSm;
        }

        if (widgetName === 'number_of_records_opt') {
            const template = this._getCurrentTemplate();
            return template && !template.numOfElFetch;
        }

        return this._super.apply(this, arguments);
    },
    /**
     * @override
     * @private
     * @returns {Promise}
     */
    _refreshPublicWidgets: function () {
        return this._super.apply(this, arguments).then(() => {
            const template = this._getCurrentTemplate();
            this.$target.find('.missing_option_warning').toggleClass(
                'd-none',
                !!template
            );
        });
    },
    /**
     * Fetches dynamic filters.
     * @private
     * @returns {Promise}
     */
    _fetchDynamicFilters: function () {
        return this._rpc({route: '/website/snippet/options_filters', params: {
            model_name: this.modelNameFilter,
            search_domain: this.contextualFilterDomain,
        }});
    },
    /**
     * Fetch dynamic filters templates.
     * @private
     * @returns {Promise}
     */
    _fetchDynamicFilterTemplates: function () {
        const filter = this.dynamicFilters[this.$target.get(0).dataset['filterId']];
        return filter ? this._rpc({route: '/website/snippet/filter_templates', params: {
            filter_name: filter.model_name.replaceAll('.', '_'),
        }}) : [];
    },
    /**
     *
     * @override
     * @private
     */
    _renderCustomXML: async function (uiFragment) {
        await this._renderDynamicFiltersSelector(uiFragment);
        await this._renderDynamicFilterTemplatesSelector(uiFragment);
    },
    /**
     * Renders the dynamic filter option selector content into the provided uiFragment.
     * @param {HTMLElement} uiFragment
     * @private
     */
    _renderDynamicFiltersSelector: async function (uiFragment) {
        if (!Object.keys(this.dynamicFilters).length) {
            const dynamicFilters = await this._fetchDynamicFilters();
            for (let index in dynamicFilters) {
                this.dynamicFilters[dynamicFilters[index].id] = dynamicFilters[index];
            }
            if (dynamicFilters.length > 0) {
                const selectedFilterId = this.$target.get(0).dataset['filterId'];
                if (!this.dynamicFilters[selectedFilterId]) {
                    this.$target.get(0).dataset['filterId'] = dynamicFilters[0].id;
                    this.isOptionDefault['filterId'] = true;
                }
            }
        }
        const filtersSelectorEl = uiFragment.querySelector('[data-name="filter_opt"]');
        return this._renderSelectUserValueWidgetButtons(filtersSelectorEl, this.dynamicFilters);
    },
    /**
     * Renders we-buttons into a SelectUserValueWidget element according to provided data.
     * @param {HTMLElement} selectUserValueWidgetElement the SelectUserValueWidget buttons
     *   have to be created into.
     * @param {JSON} data
     * @private
     */
    _renderSelectUserValueWidgetButtons: async function (selectUserValueWidgetElement, data) {
        for (let id in data) {
            const button = document.createElement('we-button');
            button.dataset.selectDataAttribute = id;
            button.innerHTML = data[id].name;
            selectUserValueWidgetElement.appendChild(button);
        }
    },
    /**
     * Renders the template option selector content into the provided uiFragment.
     * @param {HTMLElement} uiFragment
     * @private
     */
    _renderDynamicFilterTemplatesSelector: async function (uiFragment) {
        const dynamicFilterTemplates = await this._fetchDynamicFilterTemplates();
        this.dynamicFilterTemplates = {};
        for (let index in dynamicFilterTemplates) {
            this.dynamicFilterTemplates[dynamicFilterTemplates[index].key] = dynamicFilterTemplates[index];
        }
        if (dynamicFilterTemplates.length > 0) {
            const selectedTemplateId = this.$target.get(0).dataset['templateKey'];
            if (!this.dynamicFilterTemplates[selectedTemplateId]) {
                this.$target.get(0).dataset['templateKey'] = dynamicFilterTemplates[0].key;
                this.isOptionDefault['templateKey'] = true;
                this._templateUpdated(dynamicFilterTemplates[0].key, selectedTemplateId);
                await this._refreshPublicWidgets();
            }
        } else {
            await this._refreshPublicWidgets();
        }
        const templatesSelectorEl = uiFragment.querySelector('[data-name="template_opt"]');
        return this._renderSelectUserValueWidgetButtons(templatesSelectorEl, this.dynamicFilterTemplates);
    },
    /**
     * Sets default options values.
     * Method to be overridden in child components in order to set additional
     * options default values.
     * @private
     */
    _setOptionsDefaultValues: function () {
        // Unactive the editor observer, otherwise, undo of the editor will undo
        // the attribute being changed. In some case of undo, a race condition
        // with the public widget that use following property (eg.
        // numberOfElements or numberOfElementsSmallDevices) might throw an
        // exception by not finding the attribute on the element.
        this.options.wysiwyg.odooEditor.observerUnactive();
        this._setOptionValue('numberOfElements', 4);
        this._setOptionValue('numberOfElementsSmallDevices', 1);
        const filterKeys = this.$el.find("we-select[data-attribute-name='filterId'] we-selection-items we-button");
        if (filterKeys.length > 0) {
            this._setOptionValue('numberOfRecords', this.dynamicFilters[Object.keys(this.dynamicFilters)[0]].limit);
        }
        const filter = this.dynamicFilters[this.$target.get(0).dataset['filterId']];
        this._filterUpdated(filter);
        this.options.wysiwyg.odooEditor.observerActive();
    },
    /**
     * Take the new filter selection into account
     * @param filter
     * @private
     */
    _filterUpdated: function (filter) {
        if (filter && this.currentModelName !== filter.model_name) {
            this.currentModelName = filter.model_name;
            this.rerender = true;
        }
    },
    /**
     * Take the new template selection into account
     * @param newTemplate
     * @param oldTemplate
     * @private
     */
    _templateUpdated: function (newTemplate, oldTemplate) {
        if (oldTemplate) {
            this.$target.removeClass(this._getTemplateClass(oldTemplate));
        }
        this.$target.addClass(this._getTemplateClass(newTemplate));

        const template = this.dynamicFilterTemplates[newTemplate];
        if (template.numOfEl) {
            this.$target[0].dataset.numberOfElements = template.numOfEl;
        }
        if (template.numOfElSm) {
            this.$target[0].dataset.numberOfElementsSmallDevices = template.numOfElSm;
        }
        if (template.numOfElFetch) {
            this.$target[0].dataset.numberOfRecords = template.numOfElFetch;
        }
    },
    /**
     * Sets the option value.
     * @param optionName
     * @param value
     * @private
     */
    _setOptionValue: function (optionName, value) {
        const selectedTemplateId = this.$target.get(0).dataset['templateKey'];
        if (this.$target.get(0).dataset[optionName] === undefined || this.isOptionDefault[optionName]) {
            this.$target.get(0).dataset[optionName] = value;
            this.isOptionDefault[optionName] = false;
        }
        if (optionName === 'templateKey') {
            this._templateUpdated(value, selectedTemplateId);
        }
    },
});

options.registry.dynamic_snippet = dynamicSnippetOptions;

return dynamicSnippetOptions;
});
