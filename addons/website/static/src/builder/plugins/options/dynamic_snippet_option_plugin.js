import { SNIPPET_SPECIFIC_END } from "@html_builder/utils/option_sequence";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { Cache } from "@web/core/utils/cache";
import { DynamicSnippetOption } from "./dynamic_snippet_option";
import { BuilderAction } from "@html_builder/core/builder_action";

/**
 * @typedef {object} Template
 * @property {string} arrowPosition
 * @property {string} columnClasses
 * @property {string} containerClasses
 * @property {string} contentClasses
 * @property {string} extraClasses
 * @property {string} extraSnippetClasses
 * @property {string} key
 * @property {string} numberOfElements
 * @property {string} numberOfElementsSmallDevices
 * @property {string} numberOfRecords
 * @property {string} rowPerSlide
 * @property {string} thumb
 */

/**
 * @typedef { Object } DynamicSnippetOptionShared
 * @property { DynamicSnippetOptionPlugin['fetchDynamicFilters'] } fetchDynamicFilters
 * @property { DynamicSnippetOptionPlugin['fetchDynamicFilterTemplates'] } fetchDynamicFilterTemplates
 * @property { DynamicSnippetOptionPlugin['setOptionsDefaultValues'] } setOptionsDefaultValues
 * @property { DynamicSnippetOptionPlugin['updateTemplate'] } updateTemplate
 * @property { DynamicSnippetOptionPlugin['getModelNameFilter'] } getModelNameFilter
 */

/**
 * @typedef {((arg: {
 *      el: HTMLElement;
 *      template: Template;
 * }) => void)[]} dynamic_snippet_template_updated
 */

export const DYNAMIC_SNIPPET = SNIPPET_SPECIFIC_END;

class DynamicSnippetOptionPlugin extends Plugin {
    static id = "dynamicSnippetOption";
    static shared = [
        "fetchDynamicFilters",
        "fetchDynamicFilterTemplates",
        "setOptionsDefaultValues",
        "updateTemplate",
        "getModelNameFilter",
    ];
    modelNameFilter = "";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_options: [withSequence(DYNAMIC_SNIPPET, DynamicSnippetOption)],
        builder_actions: {
            DynamicFilterAction,
            DynamicFilterTemplateAction,
            CustomizeTemplateAction,
        },
        on_snippet_dropped_handlers: this.onSnippetDropped.bind(this),
        is_unremovable_selector: ".s_dynamic_snippet_title",
    };
    setup() {
        this.dynamicFiltersCache = new Cache(this._fetchDynamicFilters, JSON.stringify);
        this.dynamicFilterTemplatesCache = new Cache(
            this._fetchDynamicFilterTemplates,
            JSON.stringify
        );
    }
    destroy() {
        super.destroy();
        this.dynamicFiltersCache.invalidate();
        this.dynamicFilterTemplatesCache.invalidate();
    }
    getModelNameFilter() {
        return this.modelNameFilter;
    }
    async onSnippetDropped({ snippetEl }) {
        if (snippetEl.matches(DynamicSnippetOption.selector)) {
            await this.setOptionsDefaultValues(snippetEl, this.modelNameFilter);
        }
    }
    async setOptionsDefaultValues(snippetEl, modelNameFilter, contextualFilterDomain = []) {
        const fetchedDynamicFilters = await this.fetchDynamicFilters({
            model_name: modelNameFilter,
            search_domain: contextualFilterDomain,
        });
        const dynamicFilters = {};
        for (const dynamicFilter of fetchedDynamicFilters) {
            dynamicFilters[dynamicFilter.id] = dynamicFilter;
        }
        const fetchedDynamicFilterTemplates = await this.fetchDynamicFilterTemplates({
            filter_name: modelNameFilter.replaceAll(".", "_"),
        });
        const dynamicFilterTemplates = {};
        for (const dynamicFilterTemplate of fetchedDynamicFilterTemplates) {
            dynamicFilterTemplates[dynamicFilterTemplate.key] = dynamicFilterTemplate;
        }
        let selectedFilterId = snippetEl.dataset["filterId"];
        if (Object.keys(dynamicFilters).length > 0) {
            setDatasetIfUndefined(snippetEl, "numberOfRecords", fetchedDynamicFilters[0].limit);
            const defaultFilterId = fetchedDynamicFilters[0].id;
            if (!dynamicFilters[selectedFilterId]) {
                snippetEl.dataset["filterId"] = defaultFilterId;
                selectedFilterId = defaultFilterId;
            }
        }
        if (
            dynamicFilters[selectedFilterId] &&
            !dynamicFilterTemplates[snippetEl.dataset["templateKey"]]
        ) {
            const modelName = dynamicFilters[selectedFilterId].model_name.replaceAll(".", "_");
            const defaultFilterTemplate = fetchedDynamicFilterTemplates.find((dynamicTemplate) =>
                dynamicTemplate.key.includes(modelName)
            );
            snippetEl.dataset["templateKey"] = defaultFilterTemplate.key;
            this.updateTemplate(snippetEl, defaultFilterTemplate);
        }
    }
    getTemplateClass(templateKey) {
        return templateKey.replace(/.*\.dynamic_filter_template_/, "s_");
    }
    updateTemplate(el, template) {
        const newTemplateKey = template.key;
        const oldTemplateKey = el.dataset.templateKey;
        el.dataset.templateKey = newTemplateKey;
        if (oldTemplateKey) {
            el.classList.remove(this.getTemplateClass(oldTemplateKey));
        }
        el.classList.add(this.getTemplateClass(newTemplateKey));

        if (template.numOfEl) {
            el.dataset.numberOfElements = template.numOfEl;
        } else {
            delete el.dataset.numberOfElements;
        }
        if (template.numOfElSm) {
            el.dataset.numberOfElementsSmallDevices = template.numOfElSm;
        } else {
            delete el.dataset.numberOfElementsSmallDevices;
        }
        if (template.numOfElFetch) {
            el.dataset.numberOfRecords = template.numOfElFetch;
        }
        if (template.extraClasses) {
            el.dataset.extraClasses = template.extraClasses;
        } else {
            delete el.dataset.extraClasses;
        }
        if (template.columnClasses) {
            el.dataset.columnClasses = template.columnClasses;
        } else {
            delete el.dataset.columnClasses;
        }
        this.dispatchTo("dynamic_snippet_template_updated", { el: el, template: template });
    }
    async fetchDynamicFilters(params) {
        return this.dynamicFiltersCache.read(params);
    }
    async _fetchDynamicFilters(params) {
        return rpc("/website/snippet/options_filters", params);
    }
    async fetchDynamicFilterTemplates(params) {
        return this.dynamicFilterTemplatesCache.read(params);
    }
    async _fetchDynamicFilterTemplates(params) {
        return rpc("/website/snippet/filter_templates", params);
    }
}

export function setDatasetIfUndefined(snippetEl, optionName, value) {
    if (snippetEl.dataset[optionName] === undefined) {
        snippetEl.dataset[optionName] = value;
    }
}

export class DynamicFilterAction extends BuilderAction {
    static id = "dynamicFilter";
    static dependencies = ["dynamicSnippetOption"];
    isApplied({ editingElement: el, params }) {
        return parseInt(el.dataset.filterId) === params.id;
    }
    apply({ editingElement: el, params }) {
        el.dataset.filterId = params.id;
        if (
            !el.dataset.templateKey ||
            !el.dataset.templateKey.includes(`_${params.model_name.replaceAll(".", "_")}_`)
        ) {
            // Only if filter's model name changed
            this.dependencies.dynamicSnippetOption.updateTemplate(el, params.defaultTemplate);
        }
    }
}
export class DynamicFilterTemplateAction extends BuilderAction {
    static id = "dynamicFilterTemplate";
    static dependencies = ["dynamicSnippetOption"];
    isApplied({ editingElement: el, params }) {
        return el.dataset.templateKey === params.key;
    }
    apply({ editingElement: el, params }) {
        this.dependencies.dynamicSnippetOption.updateTemplate(el, params);
    }
}
export class CustomizeTemplateAction extends BuilderAction {
    static id = "customizeTemplate";
    isApplied({ editingElement: el, params: { mainParam: customDataKey } }) {
        const customData = JSON.parse(el.dataset.customTemplateData);
        return customData[customDataKey];
    }
    apply({ editingElement: el, params: { mainParam: customDataKey }, value }) {
        const customData = JSON.parse(el.dataset.customTemplateData);
        customData[customDataKey] = true;
        el.dataset.customTemplateData = JSON.stringify(customData);
    }
    clean({ editingElement: el, params: { mainParam: customDataKey }, value }) {
        const customData = JSON.parse(el.dataset.customTemplateData);
        customData[customDataKey] = false;
        el.dataset.customTemplateData = JSON.stringify(customData);
    }
}

registry.category("website-plugins").add(DynamicSnippetOptionPlugin.id, DynamicSnippetOptionPlugin);
