import options from "@web_editor/js/editor/snippets.options";
import { rpc } from "@web/core/network/rpc";

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
        // The target starts only after applying the correct template values
        // (e.g., numberOfElements, rowPerSlide) since its reactions are
        // inactive by default.
        return this._refreshPublicWidgets();
    },
    /**
     * @override
     */
    async start() {
        await this._super(...arguments);
        this.customTemplateData = JSON.parse(this.$target[0].dataset?.customTemplateData || "{}");
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     *
     * @see this.selectClass for parameters
     */
    async selectDataAttribute(previewMode, widgetValue, params) {
        await this._super(...arguments);
        if (params.attributeName === "filterId" && previewMode === false) {
            // Update the snippet data attributes.
            const filter = this.dynamicFilters[parseInt(widgetValue)];
            this.$target[0].dataset.numberOfRecords = filter.limit;
            // If the new filter is linked to a different model, we need to
            // adapt the current model and the snippet template accordingly.
            if (filter && this.currentModelName !== filter.model_name) {
                this.currentModelName = filter.model_name;
                await this._fetchDynamicFilterTemplates();
                if (Object.keys(this.dynamicFilterTemplates).length > 0) {
                    const selectedTemplateId = this.$target[0].dataset["templateKey"];
                    if (!this.dynamicFilterTemplates[selectedTemplateId]) {
                        this._setDefaultTemplate();
                    }
                }
                this.rerender = true;
            }
        }
        if (params.attributeName === "templateKey" && previewMode === false) {
            this._templateUpdated(widgetValue, params.activeValue);
        }
        if (params.attributeName === "snippetModel" && previewMode === false) {
            if (this.currentModelName !== widgetValue) {
                // Update the snippet data attributes (only available in the
                // "single record" mode).
                delete this.$target[0].dataset.snippetResId;
                this.currentModelName = widgetValue;
                await this._fetchDynamicFilterTemplates();
                this._setDefaultTemplate();
                this.rerender = true;
            }
        }
        if (
            params.attributeName === "numberOfRecords" &&
            widgetValue !== params.activeValue &&
            previewMode === false
        ) {
            // Changing the number of records should automatically switch to a
            // "single record" filter mode if only one record is selected, and
            // conversely, revert to the default filter mode when more than one
            // record is selected.
            const isSingleRecord = this._isSingleRecordSnippet();
            const switchMode = isSingleRecord !== (params.activeValue === "1");
            if (switchMode) {
                const titleOptionClasses = ["d-none", "justify-content-between"];
                if (isSingleRecord) {
                    // Remove useless data on the target and set the single
                    // record default values.
                    this.$target[0].dataset.snippetModel = this.currentModelName;
                    delete this.$target[0].dataset.filterId;
                    titleOptionClasses.reverse();
                } else {
                    this.$target[0].dataset.filterId = Object.entries(this.dynamicFilters).find(
                        (dynamicFilter) => dynamicFilter[1].model_name === this.currentModelName
                    )[0];
                    delete this.$target[0].dataset.snippetModel;
                    delete this.$target[0].dataset.snippetResId;
                }
                this.$target[0]
                    .querySelector(".s_dynamic_snippet_title")
                    ?.classList.replace(...titleOptionClasses);
                const canUsePreviousTemplateKey = this._previousTemplateKey &&
                    this._isModelSnippetTemplate(this._previousTemplateKey, this.currentModelName) &&
                    !!this._isSingleRecordSnippetTemplate(this._previousTemplateKey) === isSingleRecord;
                this._defaultTemplateKey = canUsePreviousTemplateKey
                    ? this._previousTemplateKey
                    : this._getDefaultTemplateKey();
                this._previousTemplateKey = this.$target[0].dataset.templateKey;
                this._setDefaultTemplate();
                this.rerender = true;
            }
            // TODO: Maybe there is a better way for setting a default record ID
            // when switching to single record mode. For now, we prevent
            // refreshing interactions until this value is set.
            if (!switchMode || !isSingleRecord) {
                this._refreshPublicWidgets();
            }
        }
    },
    /**
     * Saves the template data that will be handled later by the public widget.
     *
     * @see this.selectClass for parameters
     */
    customizeTemplateValues(previewMode, widgetValue, params) {
        this.customTemplateData[params.customizeTemplateKey] = widgetValue === "true";
        this.$target[0].dataset.customTemplateData = JSON.stringify(this.customTemplateData);
    },
    /**
     * Simply saves the selected record ID (in "single record" mode) that will
     * be handled by Interaction.
     *
     * @see this.selectClass for parameters
     */
    setSnippetResId(previewMode, widgetValue, params) {
        this.$target[0].dataset.snippetResId = widgetValue;
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
    _computeWidgetVisibility(widgetName, params) {
        switch (widgetName) {
            // Hide if exactly one filter is available: show when none to help
            // understand what is missing.
            case "filter_opt":
                return (
                    !this._isSingleRecordSnippet() && Object.keys(this.dynamicFilters).length !== 1
                );
            case "number_of_records_opt": {
                const template = this._getCurrentTemplate();
                return template && !template.numOfElFetch;
            }
            case "model_opt":
                return (
                    // Don't allow to switch models when a the target is
                    // a model specific snippet.
                    !this.modelNameFilter &&
                    this._isSingleRecordSnippet() &&
                    params.optionsPossibleValues.selectDataAttribute.filter(Boolean).length
                );
            case "record_opt":
                return this._isSingleRecordSnippet();
            case "section_title_opt":
                return !this._isSingleRecordSnippet();
            case "template_opt":
                // Hide the templates option on model specific snippets.
                return !this.modelNameFilter;
            case "cover_position_opt":
                return !!this.$target[0].querySelector(".s_dynamic_snippet_content_position");
        }
        return this._super(...arguments);
    },
    /**
     * @override
     * @private
     */
    _computeWidgetState(methodName, params) {
        if (methodName === "customizeTemplateValues") {
            return `${this.customTemplateData[params.customizeTemplateKey] || false}`;
        }
        if (methodName === "setSnippetResId" && this._isSingleRecordSnippet()) {
            // When switching to single record the first time, we need to set a
            // default ID (When no possible ID is available, the snippet will
            // display sample data).
            if (!this.$target[0].dataset.snippetResId) {
                this.$target[0].dataset.snippetResId = params.possibleValues.find(Boolean) || "";
                this._refreshPublicWidgets();
            }
            return this.$target[0].dataset.snippetResId;
        }
        return this._super(...arguments);
    },
    /**
     * @override
     * @private
     * @returns {Promise}
     */
    _refreshPublicWidgets: function () {
        const missingOptionWarning = () => {
            const template = !!this._getCurrentTemplate();
            this.$target[0]
                .querySelector(".missing_option_warning")
                ?.classList.toggle("d-none", template);
            this.$target[0].classList.toggle("o_dynamic_snippet_empty", template);
        };
        // Prevent restarting interactions when data is missing.
        const data = this.$target[0].dataset;
        const dataReady =
            data.templateKey &&
            ((this._isSingleRecordSnippet() && data.snippetModel) || data.filterId);
        if (!dataReady) {
            return missingOptionWarning();
        }
        return this._super.apply(this, arguments).then(missingOptionWarning);
    },
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
        for (const index in dynamicFilters) {
            this.dynamicFilters[dynamicFilters[index].id] = dynamicFilters[index];
        }
        this._defaultFilterId = dynamicFilters[0].id;
        // Track the snippet model updates.
        this.currentModelName = dynamicFilters[0].model_name;
    },
    /**
     * Fetch dynamic filters templates and set them  in {@link this.dynamicFilterTemplates}.
     *
     * @private
     * @returns {Promise}
     */
    async _fetchDynamicFilterTemplates() {
        const filter =
            this.dynamicFilters[this.$target[0].dataset["filterId"]] ||
            this.dynamicFilters[this._defaultFilterId];
        this.dynamicFilterTemplates = {};
        if (!filter) {
            return [];
        }
        const dynamicFilterTemplates = await rpc("/website/snippet/filter_templates", {
            filter_name: this.currentModelName.replaceAll(".", "_"),
        });
        for (const index in dynamicFilterTemplates) {
            this.dynamicFilterTemplates[dynamicFilterTemplates[index].key] =
                dynamicFilterTemplates[index];
        }
        this._defaultTemplateKey = this._getDefaultTemplateKey();
        if (!this.$target[0].dataset.templateKey) {
            // The snippet simply gets its template from a "template class"
            // when provided. Otherwise, it will use a default template.
            const snippetTemplateKeyfromClass = Object.keys(this.dynamicFilterTemplates).find(
                (key) => this.$target[0].classList.contains(this._getTemplateClass(key))
            );
            if (snippetTemplateKeyfromClass) {
                this._defaultTemplateKey = snippetTemplateKeyfromClass;
            }
        }
    },
    /**
     *
     * @override
     * @private
     */
    async _renderCustomXML(uiFragment) {
        await this._super(...arguments);
        this._renderDynamicFiltersSelector(uiFragment);
        this._renderDynamicFilterTemplatesSelector(uiFragment);
        const modelSelectorEl = uiFragment.querySelector('we-select[data-name="model_opt"]');
        const recordSelectorEl = uiFragment.querySelector('we-many2one[data-name="record_opt"]');
        const defaultModel =
            this.currentModelName || this.dynamicFilters[this._defaultFilterId]?.model_name;

        recordSelectorEl.classList.toggle("o_we_sublevel_1", !this.modelNameFilter);
        if (defaultModel) {
            // Get the default options values to handle the "single record" mode.
            modelSelectorEl.dataset.attributeDefaultValue = defaultModel;
            recordSelectorEl.dataset.model = this.$target[0].dataset.snippetModel || defaultModel;
        } else {
            modelSelectorEl.remove();
            recordSelectorEl.remove();
        }
    },
    /**
     * Renders the dynamic filter option selector content into the provided uiFragment.
     * @param {HTMLElement} uiFragment
     * @private
     */
    _renderDynamicFiltersSelector(uiFragment) {
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
    _renderSelectUserValueWidgetButtons(selectUserValueWidgetElement, data) {
        for (const id in data) {
            const button = document.createElement("we-button");
            button.dataset.selectDataAttribute = id;
            if (data[id].thumb) {
                button.dataset.img = data[id].thumb;
            } else {
                button.innerText = data[id].name;
            }
            if (data[id].help) {
                button.title = data[id].help;
            }
            selectUserValueWidgetElement.appendChild(button);
        }
    },
    /**
     * Renders the template option selector content into the provided uiFragment.
     * @param {HTMLElement} uiFragment
     * @private
     */
    _renderDynamicFilterTemplatesSelector(uiFragment) {
        const templatesSelectorEl = uiFragment.querySelector('[data-name="template_opt"]');
        // Only use model templates that are available in the snippet mode.
        const renderingTemplates = Object.keys(this.dynamicFilterTemplates)
            .filter((key) =>
                this._isSingleRecordSnippet()
                    ? this._isSingleRecordSnippetTemplate(key)
                    : !this._isSingleRecordSnippetTemplate(key)
            )
            .reduce((filter, key) => ({ ...filter, [key]: this.dynamicFilterTemplates[key] }), {});
        this._renderSelectUserValueWidgetButtons(templatesSelectorEl, renderingTemplates);
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
        if (this._isSingleRecordSnippet()) {
            this._setOptionValue("snippetModel", this.currentModelName);
            const defaultSnippetRecord =
                this._getSelectDefaultOption("record_opt")?.dataset.setSnippetResId;
            if (defaultSnippetRecord) {
                this._setOptionValue("snippetResId", defaultSnippetRecord);
            }
            this._setDefaultTemplate();
        } else {
            // The `_fetchDynamicFilters()` method should already set a default
            // filter (and `_setOptionValue()` sets the default one when the
            // snippet has no filter in its data).
            this._setOptionValue("filterId", this._defaultFilterId);
            const snippetDefaultFilter = this.dynamicFilters[this._defaultFilterId];
            // The default `numberOfRecords` => The number of records of the
            // default `filterId`.
            if (snippetDefaultFilter) {
                this._setOptionValue("numberOfRecords", snippetDefaultFilter.limit);
            }
            if (
                snippetDefaultFilter &&
                !this.dynamicFilterTemplates[this.$target[0].dataset.templateKey]
            ) {
                this._setDefaultTemplate();
            }
        }
        this.options.wysiwyg.odooEditor.observerActive();
    },
    /**
     * Sets the default template of the snippet. Depends on whether the snippet
     * is in "single record" mode or not.
     * @private
     */
    _setDefaultTemplate() {
        if (Object.keys(this.dynamicFilterTemplates).length) {
            const oldTemplateKey = this.$target[0].dataset.templateKey;
            this.$target[0].dataset.templateKey = this._defaultTemplateKey;
            this._templateUpdated(
                this._defaultTemplateKey,
                oldTemplateKey && oldTemplateKey != this._defaultTemplateKey
                    ? oldTemplateKey
                    : undefined
            );
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
        if (template.columnClasses) {
            this.$target[0].dataset.columnClasses = template.columnClasses;
        } else {
            delete this.$target[0].dataset.columnClasses;
        }
        const oldTemplate = !!oldTemplateKey && this.dynamicFilterTemplates[oldTemplateKey];
        if (oldTemplate) {
            const snippetContainerEl = this.$target[0].querySelector(".s_dynamic_snippet_container");
            const snippetContentEl = this.$target[0].querySelector(".s_dynamic_snippet_content");
            snippetContainerEl.classList.remove(...(oldTemplate.containerClasses?.split(" ") || []));
            snippetContainerEl.classList.add(...(template.containerClasses || "container").split(" "));
            snippetContentEl.classList.remove(...(oldTemplate.contentClasses?.split(" ") || []));
            snippetContentEl.classList.add(...(template.contentClasses?.split(" ") || []));
            this.$target[0].classList.remove(...(oldTemplate.extraSnippetClasses?.split(" ") || []));
            this.$target[0].classList.add(...(template.extraSnippetClasses?.split(" ") || []));
        }
    },
    /**
     * Sets the option value.
     * @param optionName
     * @param value
     * @private
     */
    _setOptionValue: function (optionName, value) {
        const selectedTemplateId = this.$target[0].dataset.templateKey;
        if (!this.$target[0].dataset[optionName]) {
            this.$target[0].dataset[optionName] = value;
        }
        if (optionName === "templateKey") {
            this._templateUpdated(value, selectedTemplateId);
        }
    },
    /**
     * Verify if the current snippet should display a single record.
     *
     * @private
     * @returns {Boolean}
     */
    _isSingleRecordSnippet() {
        // TODO: Currently, we need to verify that at least one template is
        // available for single record mode to be enabled. This check should be
        // removed once all single record templates have been added.
        return !!(
            parseInt(this.$target[0].dataset.numberOfRecords) === 1 && this._getDefaultTemplateKey()
        );
    },
    /**
     * Check if a template should be used to display single records.
     *
     * @private
     * @param {String} key The template key.
     * @returns {Boolean}
     */
    _isSingleRecordSnippetTemplate(key) {
        return key.includes("_single_");
    },
    /**
     * Check if a template can be used to display a model content.
     *
     * @private
     * @param {String} key The template key.
     * @param {String} modelName
     * @returns {Boolean}
     */
    _isModelSnippetTemplate(key, modelName) {
        return key.includes(modelName.replaceAll(".", "_"));
    },
    /**
     * Returns the default snippet template associated with the current model
     * for either single or multi-record modes.
     *
     * @private
     * @returns {String}
     */
    _getDefaultTemplateKey() {
        const currentModelName = this.$target[0].dataset.snippetModel || this.currentModelName;
        return Object.keys(this.dynamicFilterTemplates).find((key) => {
            const isSingleTemplate = this._isSingleRecordSnippetTemplate(key);
            return (
                this._isModelSnippetTemplate(key, currentModelName) &&
                (parseInt(this.$target[0].dataset.numberOfRecords) === 1
                    ? isSingleTemplate
                    : !isSingleTemplate)
            );
        });
    },
    /**
     * Returns the first option in a `<we-select/>`.
     *
     * @private
     * @param name The option name.
     * @returns {Element}
     */
    _getSelectDefaultOption(name) {
        return this.el.querySelector(`we-select[data-name='${name}'] we-selection-items we-button`);
    },
});

options.registry.dynamic_snippet = dynamicSnippetOptions;
options.registry.DynamicSnippetTitle = options.Class.extend({
    forceNoDeleteButton: true,
});

export default dynamicSnippetOptions;
