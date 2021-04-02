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
        if (params.attributeName === 'templateKey' && previewMode === false) {
            this._templateUpdated(widgetValue, params.activeValue);
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

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
        return this._super.apply(this, arguments);
    },
    /**
     * @override
     * @private
     * @returns {Promise}
     */
    _refreshPublicWidgets: function () {
        return this._super.apply(this, arguments).then(() => {
            const selectedTemplateId = this.$target.get(0).dataset['templateKey'];
            this.$target.find('.missing_option_warning').toggleClass(
                'd-none',
                !!this.dynamicFilterTemplates[selectedTemplateId]
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
        this.dynamicFilterTemplates = {};
        for (let index in dynamicFilterTemplates) {
            this.dynamicFilterTemplates[dynamicFilterTemplates[index].key] = dynamicFilterTemplates[index];
        }
        if (dynamicFilterTemplates.length > 0) {
            const selectedTemplateId = this.$target.get(0).dataset['templateKey'];
            if (!this.dynamicFilterTemplates[selectedTemplateId]) {
                this.$target.get(0).dataset['templateKey'] = dynamicFilterTemplates[0].key;
                setTimeout(() => {
                    this._templateUpdated(dynamicFilterTemplates[0].key, selectedTemplateId);
                    this._refreshPublicWidgets();
                });
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
            this._rerenderXML();
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
