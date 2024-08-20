/** @odoo-module **/

import { rpc } from "@web/core/network/rpc";
import {
    SnippetOption,
} from "@web_editor/js/editor/snippets.options";
import {
    registerWebsiteOption,
} from "@website/js/editor/snippets.registry";

export class DynamicSnippetOptions extends SnippetOption {
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
    constructor() {
        super(...arguments);
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
    }
    /**
     * @override
     */
    async willStart() {
        // TODO: @owl-options Init makes no sense in Owl options
        await this._fetchDynamicFilters();
        await this._fetchDynamicFilterTemplates();
        await super.willStart(...arguments);
        this.renderContext.dynamicFilters = this.dynamicFilters;
        this.renderContext.dynamicFilterTemplates = this.dynamicFilterTemplates;
    }
    /**
     *
     * @override
     */
    async onBuilt() {
        // Default values depend on the templates and filters available.
        // Therefore, they cannot be computed prior the start of the option.
        await this._setOptionsDefaultValues();
        // The target needs to be restarted when the correct
        // template values are applied (numberOfElements, rowPerSlide, etc.)
        return this._refreshPublicWidgets();
    }

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     *
     * @see this.selectClass for parameters
     */
    selectDataAttribute(previewMode, widgetValue, params) {
        super.selectDataAttribute(...arguments);
        if (params.attributeName === 'filterId' && previewMode === false) {
            const filter = this.dynamicFilters[parseInt(widgetValue)];
            this.$target.get(0).dataset.numberOfRecords = filter.limit;
            return this._filterUpdated(filter);
        }
        if (params.attributeName === 'templateKey' && previewMode === false) {
            this._templateUpdated(widgetValue, params.activeValue);
        }
    }

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
        await super.updateUI(...arguments);
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @returns {Template}
     */
    _getCurrentTemplate() {
        return this.dynamicFilterTemplates[this.$target.get(0).dataset['templateKey']];
    }

    _getTemplateClass(templateKey) {
        return templateKey.replace(/.*\.dynamic_filter_template_/, "s_");
    }

    /**
     *
     * @override
     * @private
     */
    _computeWidgetVisibility(widgetName, params) {
        if (widgetName === 'filter_opt') {
            // Hide if exaclty one is available: show when none to help understand what is missing
            return Object.keys(this.dynamicFilters).length !== 1;
        }

        if (widgetName === 'number_of_records_opt') {
            const template = this._getCurrentTemplate();
            return template && !template.numOfElFetch;
        }

        return super._computeWidgetVisibility(...arguments);
    }
    /**
     * @override
     * @private
     * @returns {Promise}
     */
    _refreshPublicWidgets() {
        return super._refreshPublicWidgets(...arguments).then(() => {
            const template = this._getCurrentTemplate();
            this.$target.find('.missing_option_warning').toggleClass(
                'd-none',
                !!template
            );
        });
    }
    /**
     * Fetches dynamic filters and set them in {@link this.dynamicFilters}.
     *
     * @private
     * @returns {Promise}
     */
    async _fetchDynamicFilters() {
        const dynamicFilters = await rpc('/website/snippet/options_filters', {
            model_name: this.modelNameFilter,
            search_domain: this.contextualFilterDomain,
        });
        if (!dynamicFilters.length) {
            // Additional modules are needed for dynamic filters to be defined.
            return;
        }
        for (let index in dynamicFilters) {
            this.dynamicFilters[dynamicFilters[index].id] = dynamicFilters[index];
        }
        this._defaultFilterId = dynamicFilters[0].id;
    }
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
        const dynamicFilterTemplates = await rpc('/website/snippet/filter_templates', {
            filter_name: filter.model_name.replaceAll('.', '_'),
        });
        for (let index in dynamicFilterTemplates) {
            this.dynamicFilterTemplates[dynamicFilterTemplates[index].key] = dynamicFilterTemplates[index];
        }
        this._defaultTemplateKey = dynamicFilterTemplates[0].key;
    }
    /**
     * @override
     * @private
     */
    async _getRenderContext() {
        return {
            dynamicFilter: this.dynamicFilter || {},
            dynamicFilterTemplates: this.dynamicFilterTemplates || {},
        };
    }
    /**
     * Sets default options values.
     * Method to be overridden in child components in order to set additional
     * options default values.
     * @private
     */
    async _setOptionsDefaultValues() {
        if (!this.$target[0].dataset.numberOfRecords) {
            this._setOptionValue("numberOfRecords",
                this.dynamicFilters.length ? this.dynamicFilters[Object.keys(this.dynamicFilters)[0]].limit : 4
            );
        }
        if (!this.$target[0].dataset.filterId) {
            this.$target[0].dataset["filterId"] = this._defaultFilterId;
        }
        if (!this.$target[0].dataset.templateKey) {
            this.$target[0].dataset["templateKey"] = this._defaultTemplateKey;
            this._setDefaultTemplate();
        }
    }
    /**
     * Take the new filter selection into account
     * @param filter
     * @private
     */
    async _filterUpdated(filter) {
        if (filter && this.currentModelName !== filter.model_name) {
            this.currentModelName = filter.model_name;
            await this._fetchDynamicFilterTemplates();
            this.renderContext.dynamicFilterTemplates = this.dynamicFilterTemplates;
            if (Object.keys(this.dynamicFilterTemplates).length > 0) {
                const selectedTemplateId = this.$target.get(0).dataset['templateKey'];
                if (!this.dynamicFilterTemplates[selectedTemplateId]) {
                    this._setDefaultTemplate();
                }
            }
        }
    }
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
    }

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
    }
    /**
     * Sets the option value.
     * @param optionName
     * @param value
     * @private
     */
    _setOptionValue(optionName, value) {
        const selectedTemplateId = this.$target.get(0).dataset['templateKey'];
        if (this.$target.get(0).dataset[optionName] === undefined || this.isOptionDefault[optionName]) {
            this.$target.get(0).dataset[optionName] = value;
            this.isOptionDefault[optionName] = false;
        }
        if (optionName === 'templateKey') {
            this._templateUpdated(value, selectedTemplateId);
        }
    }
}

registerWebsiteOption("DynamicSnippetOptions", {
    Class: DynamicSnippetOptions,
    template: "website.s_dynamic_snippet_option",
    selector: "[data-snippet='s_dynamic_snippet']",
});
