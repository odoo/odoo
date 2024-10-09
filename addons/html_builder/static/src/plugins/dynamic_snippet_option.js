import { Plugin } from "@html_editor/plugin";
import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { defaultBuilderComponents } from "../core/default_builder_components";
import { useDomState, useIsActiveItem } from "@html_builder/core/building_blocks/utils";
import { withSequence } from "@html_editor/utils/resource";
import { rpc } from "@web/core/network/rpc";
import { Cache } from "@web/core/utils/cache";

class DynamicSnippetOptionPlugin extends Plugin {
    static id = "DynamicSnippetOption";
    static shared = ["getComponentProps"];
    resources = {
        builder_options: [
            withSequence(10, {
                OptionComponent: DynamicSnippetOption,
                props: this.getComponentProps(),
                selector: ".s_dynamic_snippet",
            }),
        ],
        builder_actions: this.getActions(),
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
    getComponentProps() {
        return {
            fetchDynamicFilters: this.fetchDynamicFilters.bind(this),
            fetchDynamicFilterTemplates: this.fetchDynamicFilterTemplates.bind(this),
        };
    }
    getActions() {
        return {
            dynamicFilter: {
                isApplied: ({ editingElement: el, param }) =>
                    parseInt(el.dataset.filterId) === param.id,
                apply: ({ editingElement: el, param }) => {
                    el.dataset.filterId = param.id;
                    if (
                        !el.dataset.templateKey ||
                        !el.dataset.templateKey.includes(
                            `_${param.model_name.replaceAll(".", "_")}_`
                        )
                    ) {
                        // Only if filter's model name changed
                        this.updateTemplate(el, param.defaultTemplate);
                    }
                },
            },
            dynamicFilterTemplate: {
                isApplied: ({ editingElement: el, param }) => el.dataset.templateKey === param.key,
                apply: ({ editingElement: el, param }) => {
                    this.updateTemplate(el, param);
                },
            },
            customizeTemplate: {
                isApplied: ({ editingElement: el, param }) => {
                    const customData = JSON.parse(el.dataset.customTemplateData);
                    return customData[param];
                },
                apply: ({ editingElement: el, param, value }) => {
                    const customData = JSON.parse(el.dataset.customTemplateData);
                    customData[param] = true;
                    el.dataset.customTemplateData = JSON.stringify(customData);
                },
                clean: ({ editingElement: el, param, value }) => {
                    const customData = JSON.parse(el.dataset.customTemplateData);
                    customData[param] = false;
                    el.dataset.customTemplateData = JSON.stringify(customData);
                },
            },
        };
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

registry.category("website-plugins").add(DynamicSnippetOptionPlugin.id, DynamicSnippetOptionPlugin);

export class DynamicSnippetOption extends Component {
    static template = "html_builder.DynamicSnippetOption";
    static components = { ...defaultBuilderComponents };
    static props = {
        fetchDynamicFilters: Function,
        fetchDynamicFilterTemplates: Function,
        slots: { type: Object, optional: true },
    };

    setup() {
        this.isActiveItem = useIsActiveItem();
        // specify model name in subclasses to filter the list of available model record filters
        this.modelNameFilter = undefined;
        this.contextualFilterDomain = [];
        // Indicates that some current options are a default selection.
        this.isOptionDefault = {};

        onWillStart(async () => {
            await this.fetchDynamicFiltersAndTemplates();
        });
        this.state = useState({
            defaultFilterId: undefined,
            dynamicFilters: {}, // per id, to locate default filter
            dynamicFilterTemplates: [],
        });
        this.domState = useDomState(() => ({
            filterId: this.env.getEditingElement().dataset.filterId,
        }));
    }

    async fetchDynamicFiltersAndTemplates() {
        const dynamicFilters = await this.props.fetchDynamicFilters({
            model_name: this.modelNameFilter,
            search_domain: this.contextualFilterDomain,
        });
        if (!dynamicFilters.length) {
            // Additional modules are needed for dynamic filters to be defined.
            return;
        }
        const uniqueModelName = new Set();
        for (const dynamicFilter of dynamicFilters) {
            this.state.dynamicFilters[dynamicFilter.id] = dynamicFilter;
            uniqueModelName.add(dynamicFilter.model_name);
        }
        this.state.defaultFilterId = dynamicFilters[0].id;
        const templateFilter = uniqueModelName.length === 1 ? dynamicFilters[0].model_name : "";
        const dynamicFilterTemplates = await this.props.fetchDynamicFilterTemplates({
            filter_name: templateFilter.replaceAll(".", "_"),
        });
        this.state.dynamicFilterTemplates.push(...dynamicFilterTemplates);
        const defaultTemplatePerModel = {};
        for (const modelName of uniqueModelName) {
            for (const template of dynamicFilterTemplates) {
                if (template.key.includes(`_${modelName.replaceAll(".", "_")}_`)) {
                    defaultTemplatePerModel[modelName] = template;
                    break;
                }
            }
        }
        for (const dynamicFilter of dynamicFilters) {
            dynamicFilter.defaultTemplate = defaultTemplatePerModel[dynamicFilter.model_name];
        }
    }
    getFilteredTemplates() {
        const namePattern =
            "_" +
            this.state.dynamicFilters[
                this.domState.filterId || this.state.defaultFilterId
            ].model_name.replaceAll(".", "_") +
            "_";
        return this.state.dynamicFilterTemplates.filter((template) =>
            template.key.includes(namePattern)
        );
    }
}
