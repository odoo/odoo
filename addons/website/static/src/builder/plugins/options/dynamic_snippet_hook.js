import { useEnv } from "@web/owl2/utils";
import { useDomState } from "@html_builder/core/utils";
import { onWillStart } from "@odoo/owl";
import {
    dynamicContentOfDynamicSnippet,
    getSharedSnippetArg,
} from "./dynamic_snippet_option_plugin";

export function useDynamicSnippetOption() {
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
        domState.isSingleMode = dynamicSnippetUtils.isSingleModeSnippet({
            dynamicEl: domState.dynamicEl,
        });
    });
    const dynamicFilterTemplates = {};
    // Common functions to handle dynamic snippets filters & templates...
    const dynamicSnippetUtils = env.editor.shared.dynamicSnippetOption;
    const modelNameFilter = dynamicSnippetUtils.getModelNameFilter(env.getEditingElement());
    const dynamicFilters = {};
    const domState = useDomState((editingElement) => {
        const dynamicEl = dynamicContentOfDynamicSnippet(editingElement);
        return {
            dynamicEl,
            filterId: getSharedSnippetArg(dynamicEl, "filter_id"),
            snippetModel: getSharedSnippetArg(dynamicEl, "res_model") || modelNameFilter,
            limit: getSharedSnippetArg(dynamicEl, "limit"),
            templateKey: getSharedSnippetArg(dynamicEl, "content_template"),
            isSingleMode: dynamicSnippetUtils.isSingleModeSnippet({ dynamicEl }),
        };
    });

    async function fetchDynamicFiltersAndTemplates() {
        const fetchedDynamicFilters = await dynamicSnippetUtils.fetchDynamicFilters({
            model_name: modelNameFilter,
            search_domain: env.editor.processThrough(
                "dynamic_filter_contextual_domain_processors",
                [],
                { snippetEl: env.getEditingElement() }
            ),
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
        const snippetModel = domState.snippetModel || dynamicFilters[domState.filterId]?.model_name;
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
        modelNameFilter,
        dynamicFilters,
        domState,
        getFilteredTemplates,
        showFilterOption,
        ...dynamicSnippetUtils,
    };
}
