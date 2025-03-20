import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { onWillStart, useState } from "@odoo/owl";

export class DynamicSnippetOption extends BaseOptionComponent {
    static template = "html_builder.DynamicSnippetOption";
    static props = {
        fetchDynamicFilters: Function,
        fetchDynamicFilterTemplates: Function,
        slots: { type: Object, optional: true },
    };

    setup() {
        super.setup();
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
