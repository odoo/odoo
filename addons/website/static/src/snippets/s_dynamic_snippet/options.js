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
    },
    /**
     *
     * @override
     */
    onBuilt: function () {
        this._setOptionsDefaultValues();
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
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

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
        return this._super.apply(this, arguments);
    },
    /**
     * @override
     * @private
     * @returns {Promise}
     */
    _refreshPublicWidgets: function () {
        return this._super.apply(this, arguments).then(() => {
            const templateKeys = this.$el ? this.$el.find("we-select[data-attribute-name='templateKey'] we-selection-items we-button") : [];
            this.$target.find('.missing_option_warning').toggleClass(
                'd-none',
                templateKeys.length > 0
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
        for (let index in dynamicFilterTemplates) {
            this.dynamicFilterTemplates[dynamicFilterTemplates[index].key] = dynamicFilterTemplates[index];
        }
        if (dynamicFilterTemplates.length > 0) {
            const selectedTemplateId = this.$target.get(0).dataset['templateKey'];
            if (!this.dynamicFilterTemplates[selectedTemplateId]) {
                this.$target.get(0).dataset['templateKey'] = dynamicFilterTemplates[0].key;
                this._refreshPublicWidgets();
            }
        } else {
            this._refreshPublicWidgets();
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
        this._setOptionValue('numberOfElements', 4);
        this._setOptionValue('numberOfElementsSmallDevices', 1);
        const filterKeys = this.$el.find("we-select[data-attribute-name='filterId'] we-selection-items we-button");
        if (filterKeys.length > 0) {
            this._setOptionValue('numberOfRecords', this.dynamicFilters[Object.keys(this.dynamicFilters)[0]].limit);
        }
        const filter = this.dynamicFilters[this.$target.get(0).dataset['filterId']];
        this._filterUpdated(filter);
    },
    /**
     * Take the new filter selection into account
     * @param filter
     * @private
     */
    _filterUpdated: function (filter) {
        if (filter && this.currentModelName !== filter.model_name) {
            this.currentModelName = filter.model_name;
            this._rerenderXML();
        }
    },
    /**
     * Sets the option value.
     * @param optionName
     * @param value
     * @private
     */
    _setOptionValue: function (optionName, value) {
        if (this.$target.get(0).dataset[optionName] === undefined) {
            this.$target.get(0).dataset[optionName] = value;
        }
    },
});

options.registry.dynamic_snippet = dynamicSnippetOptions;

return dynamicSnippetOptions;
});
