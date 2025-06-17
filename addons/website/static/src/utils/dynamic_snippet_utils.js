import { rpc } from '@web/core/network/rpc';

/**
 * Set default values for dynamic snippets
 * Replicates the logic from DynamicSnippetOptionPlugin for use in interactions
 */
export async function setDynamicSnippetDefaults(
    snippetEl,
    modelNameFilter = '',
    contextualFilterDomain = []
) {
    if (snippetEl.dataset.filterId && snippetEl.dataset.templateKey) {
        return;
    }
    // Fetch dynamic filters
    const fetchedDynamicFilters = await rpc('/website/snippet/options_filters', {
        model_name: modelNameFilter,
        search_domain: contextualFilterDomain,
    });
    
    // Fetch dynamic filter templates  
    const fetchedDynamicFilterTemplates = await rpc('/website/snippet/filter_templates', {
        filter_name: modelNameFilter.replaceAll('.', '_'),
    });
    
    // Build lookup objects (same logic as plugin)
    const dynamicFilters = {};
    for (const dynamicFilter of fetchedDynamicFilters) {
        dynamicFilters[dynamicFilter.id] = dynamicFilter;
    }
    
    const dynamicFilterTemplates = {};
    for (const dynamicFilterTemplate of fetchedDynamicFilterTemplates) {
        dynamicFilterTemplates[dynamicFilterTemplate.key] = dynamicFilterTemplate;
    }

    // Set default filterId (exact logic from plugin)
    let selectedFilterId = snippetEl.dataset['filterId'];
    if (Object.keys(dynamicFilters).length > 0) {
        setDatasetIfUndefined(snippetEl, 'numberOfRecords', fetchedDynamicFilters[0].limit);
        const defaultFilterId = fetchedDynamicFilters[0].id;
        if (!dynamicFilters[selectedFilterId]) {
            snippetEl.dataset['filterId'] = defaultFilterId;
            selectedFilterId = defaultFilterId;
        }
    }

    // Set default templateKey (exact logic from plugin)
    if (
        dynamicFilters[selectedFilterId] &&
        !dynamicFilterTemplates[snippetEl.dataset['templateKey']]
    ) {
        const modelName = dynamicFilters[selectedFilterId].model_name.replaceAll('.', '_');
        const defaultFilterTemplate = fetchedDynamicFilterTemplates.find((dynamicTemplate) =>
            dynamicTemplate.key.includes(modelName)
        );

        if (defaultFilterTemplate) {
            snippetEl.dataset['templateKey'] = defaultFilterTemplate.key;
            updateTemplate(snippetEl, defaultFilterTemplate);
        }
    }

}

/**
 * Update template settings on element (extracted from plugin logic)
 */
function updateTemplate(el, template) {
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

/**
 * Helper function to set dataset value.
 */
export function setDatasetIfUndefined(snippetEl, optionName, value) {
    
    if (snippetEl.dataset[optionName] === undefined) {
        snippetEl.dataset[optionName] = value;
    }
}
