import { Cache } from '@web/core/utils/cache';
import { rpc } from '@web/core/network/rpc';

const dynamicFiltersCache = new Cache(_fetchDynamicFilters, JSON.stringify);
const dynamicFilterTemplatesCache = new Cache(_fetchDynamicFilterTemplates, JSON.stringify);

export async function setOptionsDefaultValues(
    snippetEl,
    modelNameFilter,
    contextualFilterDomain = []
) {
    const fetchedDynamicFilters = await fetchDynamicFilters({
        model_name: modelNameFilter,
        search_domain: contextualFilterDomain,
    });
    const dynamicFilters = {};
    for (const dynamicFilter of fetchedDynamicFilters) {
        dynamicFilters[dynamicFilter.id] = dynamicFilter;
    }
    const fetchedDynamicFilterTemplates = await fetchDynamicFilterTemplates({
        filter_name: modelNameFilter.replaceAll('.', '_'),
    });
    const dynamicFilterTemplates = {};
    for (const dynamicFilterTemplate of fetchedDynamicFilterTemplates) {
        dynamicFilterTemplates[dynamicFilterTemplate.key] = dynamicFilterTemplate;
    }
    let selectedFilterId = snippetEl.dataset['filterId'];
    if (Object.keys(dynamicFilters).length > 0) {
        setDatasetIfUndefined(snippetEl, 'numberOfRecords', fetchedDynamicFilters[0].limit);
        const defaultFilterId = fetchedDynamicFilters[0].id;
        if (!dynamicFilters[selectedFilterId]) {
            snippetEl.dataset['filterId'] = defaultFilterId;
            selectedFilterId = defaultFilterId;
        }
    }
    if (
        dynamicFilters[selectedFilterId] &&
        !dynamicFilterTemplates[snippetEl.dataset['templateKey']]
    ) {
        const modelName = dynamicFilters[selectedFilterId].model_name.replaceAll('.', '_');
        const defaultFilterTemplate = fetchedDynamicFilterTemplates.find((dynamicTemplate) =>
            dynamicTemplate.key.includes(modelName)
        );
        snippetEl.dataset['templateKey'] = defaultFilterTemplate.key;
        updateTemplate(snippetEl, defaultFilterTemplate);
    }
}

function getTemplateClass(templateKey) {
    return templateKey.replace(/.*\.dynamic_filter_template_/, 's_');
}

export function updateTemplate(el, template) {
    const newTemplateKey = template.key;
    const oldTemplateKey = el.dataset.templateKey;
    el.dataset.templateKey = newTemplateKey;
    if (oldTemplateKey) {
        el.classList.remove(getTemplateClass(oldTemplateKey));
    }
    el.classList.add(getTemplateClass(newTemplateKey));

    const attributeMapping = [
        ['numOfEl', 'numberOfElements'],
        ['numOfElSm', 'numberOfElementsSmallDevices'],
        ['numOfElFetch', 'numberOfRecords'],
        ['extraClasses', 'extraClasses'],
        ['columnClasses', 'columnClasses'],
    ];

    for (const [templateProp, dataAttr] of attributeMapping) {
        const value = template[templateProp];
        if (value != null) {
            el.dataset[dataAttr] = value;
        } else if (templateProp !== 'numOfElFetch') {
            delete el.dataset[dataAttr];
        }
    }
    // this.dispatchTo('dynamic_snippet_template_updated', { el: el, template: template });
}


export async function fetchDynamicFilters(params) {
    return dynamicFiltersCache.read(params);
}
async function _fetchDynamicFilters(params) {
    return rpc('/website/snippet/options_filters', params);
}
export async function fetchDynamicFilterTemplates(params) {
    return dynamicFilterTemplatesCache.read(params);
}
async function _fetchDynamicFilterTemplates(params) {
    return rpc('/website/snippet/filter_templates', params);
}


export function setDatasetIfUndefined(snippetEl, optionName, value) {
    if (snippetEl.dataset[optionName] === undefined) {
        snippetEl.dataset[optionName] = value;
    }
}
