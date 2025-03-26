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
    
    // Build lookup objects
    const dynamicFilters = Object.fromEntries(fetchedDynamicFilters.map(f => [f.id, f]));
    const dynamicFilterTemplates = Object.fromEntries(
        fetchedDynamicFilterTemplates.map(t => [t.key, t])
    );

    // Set default filterId
    let selectedFilterId = snippetEl.dataset.filterId;
    if (Object.keys(dynamicFilters).length > 0) {
        setDatasetIfUndefined(snippetEl, 'numberOfRecords', fetchedDynamicFilters[0].limit);
        const defaultFilterId = fetchedDynamicFilters[0].id;
        if (!dynamicFilters[selectedFilterId]) {
            snippetEl.dataset.filterId = defaultFilterId;
            selectedFilterId = defaultFilterId;
        }
    }

    // Set default templateKey
    if (
        dynamicFilters[selectedFilterId] &&
        !dynamicFilterTemplates[snippetEl.dataset.templateKey]
    ) {
        const modelName = dynamicFilters[selectedFilterId].model_name.replaceAll('.', '_');
        const defaultFilterTemplate = fetchedDynamicFilterTemplates.find(
            (dynamicTemplate) => dynamicTemplate.key.includes(modelName)
        );

        if (defaultFilterTemplate) {
            snippetEl.dataset.templateKey = defaultFilterTemplate.key;
            updateTemplate(snippetEl, defaultFilterTemplate);
        }
    }
}

/**
 * Update template settings on element
 */
function updateTemplate(el, template) {
    const templateClass = template.key.replace(/.*\.dynamic_filter_template_/, 's_');
    el.classList.add(templateClass || '');
    const attributeMapping = [
        ['numOfEl', 'numberOfElements'],
        ['numOfElSm', 'numberOfElementsSmallDevices'],
        ['numOfElFetch', 'numberOfRecords'],
        ['extraClasses', 'extraClasses'],
        ['columnClasses', 'columnClasses'],
    ];
    for (const [templateProp, dataAttr] of attributeMapping) {
        if (template[templateProp]) {
            el.dataset[dataAttr] = template[templateProp];
        }
    }
}

/**
 * Helper function to set dataset value.
 */
function setDatasetIfUndefined(snippetEl, optionName, value) {
    if (snippetEl.dataset[optionName] === undefined) {
        snippetEl.dataset[optionName] = value;
    }
}
