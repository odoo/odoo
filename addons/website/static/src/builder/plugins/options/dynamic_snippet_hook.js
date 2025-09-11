import { useDomState } from "@html_builder/core/utils";
import { onWillStart, useEnv } from "@odoo/owl";

export function useDynamicSnippetOption(modelNameFilter, contextualFilterDomain = []) {
    const env = useEnv();
    onWillStart(async () => {
        await fetchDynamicFiltersAndTemplates();
        // TODO: For now, a snippet is considered in "single mode" only when one
        // record is selected and at least one "single template" is available
        // for its model (which requires templates to be already fetched...).
        // The snippet automatically switches to multi-record templates but with
        // one item if it has no layouts for single mode. This can be improved
        // once single templates are added for all dynamic snippet models, and
        // the selection of one record will be enough.
        domState.isSingleMode = dynamicSnippetUtils.isSingleModeSnippet(domState);
    });
    const dynamicFilterTemplates = {};
    // Common functions to handle dynamic snippets filters & templates...
    const dynamicSnippetUtils = env.editor.shared.dynamicSnippetOption;
    const dynamicFilters = {};
    const domState = useDomState((editingElement) => ({
        filterId: editingElement.dataset.filterId,
        snippetModel: editingElement.dataset.snippetModel || modelNameFilter,
        numberOfRecords: parseInt(editingElement.dataset.numberOfRecords),
        templateKey: editingElement.dataset.templateKey,
        isSingleMode: dynamicSnippetUtils.isSingleModeSnippet(editingElement.dataset),
    }));

    async function fetchDynamicFiltersAndTemplates() {
        const fetchedDynamicFilters = await dynamicSnippetUtils.fetchDynamicFilters({
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
        const fetchedDynamicFilterTemplates =
            await dynamicSnippetUtils.fetchDynamicSnippetTemplates(modelNameFilter);
        for (const dynamicFilterTemplate of fetchedDynamicFilterTemplates) {
            dynamicFilterTemplates[dynamicFilterTemplate.key] = dynamicFilterTemplate;
        }
        const defaultTemplatePerModel = {};
        for (const modelName of uniqueModelName) {
            for (const template of fetchedDynamicFilterTemplates) {
                if (dynamicSnippetUtils.isModelSnippetTemplate(template.key, modelName)) {
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
        const snippetModel = domState.snippetModel || dynamicFilters[domState.filterId].model_name;
        return Object.values(dynamicFilterTemplates).filter(({ key }) => {
            const isModelTemplate = dynamicSnippetUtils.isModelSnippetTemplate(key, snippetModel);
            const isSingleModeTemplate = dynamicSnippetUtils.isSingleModeSnippetTemplate(key);
            return (
                isModelTemplate &&
                (domState.isSingleMode ? isSingleModeTemplate : !isSingleModeTemplate)
            );
        });
    }
    function showFilterOption() {
        return !domState.isSingleMode && Object.values(dynamicFilters).length > 1;
    }

    return {
        dynamicFilters,
        domState,
        getFilteredTemplates,
        showFilterOption,
        ...dynamicSnippetUtils,
    };
}
