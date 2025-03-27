import { useDomState } from "@html_builder/core/utils";
import { onWillStart, useEnv } from "@odoo/owl";

export function useDynamicSnippetOption(modelNameFilter, contextualFilterDomain = []) {
    const env = useEnv();
    onWillStart(async () => {
        await fetchDynamicFiltersAndTemplates();
    });
    const dynamicFilterTemplates = {};
    let defaultFilterId;
    const dynamicFilters = {};
    const domState = useDomState((editingElement) => ({
        filterId: editingElement.dataset.filterId,
    }));

    async function fetchDynamicFiltersAndTemplates() {
        const fetchedDynamicFilters =
            await env.editor.shared.dynamicSnippetOption.fetchDynamicFilters({
                model_name: modelNameFilter,
                search_domain: contextualFilterDomain,
            });
        if (!fetchedDynamicFilters.length) {
            // Additional modules are needed for dynamic filters to be defined.
            return;
        }
        const uniqueModelName = new Set();
        for (const dynamicFilter of fetchedDynamicFilters) {
            dynamicFilters[dynamicFilter.id] = dynamicFilter;
            uniqueModelName.add(dynamicFilter.model_name);
        }
        defaultFilterId = fetchedDynamicFilters[0].id;
        const fetchedDynamicFilterTemplates =
            await env.editor.shared.dynamicSnippetOption.fetchDynamicFilterTemplates({
                filter_name: modelNameFilter.replaceAll(".", "_"),
            });
        for (const dynamicFilterTemplate of fetchedDynamicFilterTemplates) {
            dynamicFilterTemplates[dynamicFilterTemplate.key] = dynamicFilterTemplate;
        }
        const defaultTemplatePerModel = {};
        for (const modelName of uniqueModelName) {
            for (const template of fetchedDynamicFilterTemplates) {
                if (template.key.includes(`_${modelName.replaceAll(".", "_")}_`)) {
                    defaultTemplatePerModel[modelName] = template;
                    break;
                }
            }
        }
        for (const dynamicFilter of fetchedDynamicFilters) {
            dynamicFilter.defaultTemplate = defaultTemplatePerModel[dynamicFilter.model_name];
        }
    }

    function getFilteredTemplates() {
        if (!Object.values(dynamicFilterTemplates).length) {
            return [];
        }
        const namePattern = `_${dynamicFilters[
            domState.filterId || defaultFilterId
        ].model_name.replaceAll(".", "_")}_`;
        return Object.values(dynamicFilterTemplates).filter((template) =>
            template.key.includes(namePattern)
        );
    }
    function showFilterOption() {
        return Object.values(dynamicFilters).length > 1;
    }

    return {
        dynamicFilters,
        domState,
        getFilteredTemplates,
        showFilterOption,
    };
}
