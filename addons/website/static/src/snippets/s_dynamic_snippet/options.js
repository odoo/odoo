odoo.define('website.s_dynamic_snippet_options', function (require) {
'use strict';

const options = require('web_editor.snippets.options');

const dynamicSnippetOptions = options.Class.extend({
    /**
     * This type defines the template infos retrieved from
     * @see /website/snippet/filter_templates
     * Used for
     * @see this.dynamicFilterTemplates
     * @typedef {Object} Template - definition of a dynamic snippet template
     * @property {string} key - key of the template
     * @property {string} numOfEl - number of elements on desktop
     * @property {string} numOfElSm - number of elements on mobile
     * @property {string} numOfElFetch - number of elements to fetch
     * @property {string} rowPerSlide - number of rows per slide
     * @property {string} arrowPosition - position of the arrows
     * @property {string} extraClasses - classes to be added to the <section>
     */

    /**
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
        /** @type {Object.<string, Template>} - key is the key of the template */
        this.dynamicFilterTemplates = {};
        // Indicates that some current options are a default selection.
        this.isOptionDefault = {};
    },
    /**
     * @override
     */
    async willStart() {
        const _super = this._super.bind(this);
        await this._fetchDynamicFilters();
        await this._fetchDynamicFilterTemplates();
        return _super(...arguments);
    },
    /**
     *
     * @override
     */
    async onBuilt() {
        // Default values depend on the templates and filters available.
        // Therefore, they cannot be computed prior the start of the option.
        await this._setOptionsDefaultValues();
        // TODO Remove in master: adapt dropped snippet template.
        const classList = [...this.$target[0].classList];
        if (classList.includes('d-none') && !classList.some(className => className.match(/^d-(md|lg)-(?!none)/))) {
            // Remove the 'd-none' of the old template if it is not related to
            // the visible on mobile option.
            this.$target[0].classList.remove('d-none');
        }
        // The target needs to be restarted when the correct
        // template values are applied (numberOfElements, rowPerSlide, etc.)
        return this._refreshPublicWidgets();
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
            return this._filterUpdated(filter);
        }
        if (params.attributeName === 'templateKey' && previewMode === false) {
            this._templateUpdated(widgetValue, params.activeValue);
        }
        // TODO adapt in master
        if (params.attributeName === 'numberOfRecords' && previewMode === false) {
            this.$target.get(0).dataset.forceMinimumMaxLimitTo16 = '1';
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

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @returns {Template}
     */
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
     * Fetches dynamic filters and set them in {@link this.dynamicFilters}.
     *
     * @private
     * @returns {Promise}
     */
    async _fetchDynamicFilters() {
        const dynamicFilters = await this._rpc({route: '/website/snippet/options_filters', params: {
            model_name: this.modelNameFilter,
            search_domain: this.contextualFilterDomain,
        }});
        if (!dynamicFilters.length) {
            // Additional modules are needed for dynamic filters to be defined.
            return;
        }
        for (let index in dynamicFilters) {
            this.dynamicFilters[dynamicFilters[index].id] = dynamicFilters[index];
        }
        this._defaultFilterId = dynamicFilters[0].id;
    },
    /**
     * Fetch dynamic filters templates and set them  in {@link this.dynamicFilterTemplates}.
     *
     * @private
     * @returns {Promise}
     */
    async _fetchDynamicFilterTemplates() {
        const filter = this.dynamicFilters[this.$target.get(0).dataset['filterId']] || this.dynamicFilters[this._defaultFilterId];
        this.dynamicFilterTemplates = {};
        if (!filter) {
            return [];
        }
        const dynamicFilterTemplates = await this._rpc({route: '/website/snippet/filter_templates', params: {
            filter_name: filter.model_name.replaceAll('.', '_'),
        }});
        for (let index in dynamicFilterTemplates) {
            this.dynamicFilterTemplates[dynamicFilterTemplates[index].key] = dynamicFilterTemplates[index];
        }
        this._defaultTemplateKey = dynamicFilterTemplates[0].key;
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
        const filtersSelectorEl = uiFragment.querySelector('[data-name="filter_opt"]');
        return this._renderSelectUserValueWidgetButtons(filtersSelectorEl, this.dynamicFilters);
    },
    /**
     * Renders we-buttons into a SelectUserValueWidget element according to provided data.
     * @param {HTMLElement} selectUserValueWidgetElement the SelectUserValueWidget buttons
     *   have to be created into.
     * @param {Object} data
     * @private
     */
    _renderSelectUserValueWidgetButtons: async function (selectUserValueWidgetElement, data) {
        for (let id in data) {
            const button = document.createElement('we-button');
            button.dataset.selectDataAttribute = id;
            if (data[id].thumb) {
                button.dataset.img = data[id].thumb;
            } else {
                button.innerText = data[id].name;
            }
            selectUserValueWidgetElement.appendChild(button);
        }
    },
    /**
     * Renders the template option selector content into the provided uiFragment.
     * @param {HTMLElement} uiFragment
     * @private
     */
    _renderDynamicFilterTemplatesSelector: async function (uiFragment) {
        const templatesSelectorEl = uiFragment.querySelector('[data-name="template_opt"]');
        return this._renderSelectUserValueWidgetButtons(templatesSelectorEl, this.dynamicFilterTemplates);
    },
    /**
     * Sets default options values.
     * Method to be overridden in child components in order to set additional
     * options default values.
     * @private
     */
    async _setOptionsDefaultValues() {
        // Unactive the editor observer, otherwise, undo of the editor will undo
        // the attribute being changed. In some case of undo, a race condition
        // with the public widget that use following property (eg.
        // numberOfElements or numberOfElementsSmallDevices) might throw an
        // exception by not finding the attribute on the element.
        this.options.wysiwyg.odooEditor.observerUnactive();
        const filterKeys = this.$el.find("we-select[data-attribute-name='filterId'] we-selection-items we-button");
        if (filterKeys.length > 0) {
            this._setOptionValue('numberOfRecords', this.dynamicFilters[Object.keys(this.dynamicFilters)[0]].limit);
        }
        let selectedFilterId = this.$target.get(0).dataset['filterId'];
        if (Object.keys(this.dynamicFilters).length > 0) {
            if (!this.dynamicFilters[selectedFilterId]) {
                this.$target.get(0).dataset['filterId'] = this._defaultFilterId;
                this.isOptionDefault['filterId'] = true;
                selectedFilterId = this._defaultFilterId;
            }
        }
        if (this.dynamicFilters[selectedFilterId] &&
                !this.dynamicFilterTemplates[this.$target.get(0).dataset['templateKey']]) {
            this._setDefaultTemplate();
        }
        this.options.wysiwyg.odooEditor.observerActive();
    },
    /**
     * Take the new filter selection into account
     * @param filter
     * @private
     */
    async _filterUpdated(filter) {
        if (filter && this.currentModelName !== filter.model_name) {
            this.currentModelName = filter.model_name;
            await this._fetchDynamicFilterTemplates();
            if (Object.keys(this.dynamicFilterTemplates).length > 0) {
                const selectedTemplateId = this.$target.get(0).dataset['templateKey'];
                if (!this.dynamicFilterTemplates[selectedTemplateId]) {
                    this._setDefaultTemplate();
                }
            }
            this.rerender = true;
        }
    },
    /**
     * Sets the default filter template.
     * @private
     */
    _setDefaultTemplate() {
        if (Object.keys(this.dynamicFilterTemplates).length) {
            this.$target.get(0).dataset['templateKey'] = this._defaultTemplateKey;
            this.isOptionDefault['templateKey'] = true;
            this._templateUpdated(this._defaultTemplateKey);
        }
    },

    /**
     * Take the new template selection into account
     * @param {String} newTemplateKey
     * @param {String} [oldTemplateKey]
     * @private
     */
    _templateUpdated(newTemplateKey, oldTemplateKey) {
        if (oldTemplateKey) {
            this.$target.removeClass(this._getTemplateClass(oldTemplateKey));
        }
        this.$target.addClass(this._getTemplateClass(newTemplateKey));

        const template = this.dynamicFilterTemplates[newTemplateKey];
        if (template.numOfEl) {
            this.$target[0].dataset.numberOfElements = template.numOfEl;
        } else {
            delete this.$target[0].dataset.numberOfElements;
        }
        if (template.numOfElSm) {
            this.$target[0].dataset.numberOfElementsSmallDevices = template.numOfElSm;
        } else {
            delete this.$target[0].dataset.numberOfElementsSmallDevices;
        }
        if (template.numOfElFetch) {
            this.$target[0].dataset.numberOfRecords = template.numOfElFetch;
        }
        if (template.extraClasses) {
            this.$target[0].dataset.extraClasses = template.extraClasses;
        } else {
            delete this.$target[0].dataset.extraClasses;
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
