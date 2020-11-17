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
        this.dynamicFilters = {};
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
            this.$target.get(0).dataset.numberOfRecords = this.dynamicFilters[parseInt(widgetValue)].limit;
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Fetches dynamic filters.
     * @private
     * @returns {Promise}
     */
    _fetchDynamicFilters: function () {
		return this._rpc({route: '/website/snippet/options_filters'});
    },
    /**
     * Fetch dynamic filters templates.
     * @private
     * @returns {Promise}
     */
    _fetchDynamicFilterTemplates: function () {
        return this._rpc({route: '/website/snippet/filter_templates'});
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
        const dynamicFilters = await this._fetchDynamicFilters();
        for (let index in dynamicFilters) {
            this.dynamicFilters[dynamicFilters[index].id] = dynamicFilters[index];
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
