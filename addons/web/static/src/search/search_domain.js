// @ts-check

/** @module search/search_domain - Domain computation utilities for SearchModel */

import { Domain } from "@web/core/domain";

import { constructDateDomain } from "./utils/dates";
/**
 * Compute the domain based on the current active categories.
 * If `excludedCategoryId` is provided, that category is excluded.
 *
 * @param {Iterable} categories - iterable of category sections
 * @param {Object} searchViewFields
 * @param {number} [excludedCategoryId]
 * @returns {Array[]}
 */
export function computeCategoryDomain(
    categories,
    searchViewFields,
    excludedCategoryId,
) {
    const domain = [];
    for (const category of categories) {
        if (category.id === excludedCategoryId || !category.activeValueId) {
            continue;
        }
        const field = searchViewFields[category.fieldName];
        const operator =
            field.type === "many2one" && category.parentField ? "child_of" : "=";
        domain.push([category.fieldName, operator, category.activeValueId]);
    }
    return domain;
}

/**
 * Compute the domain based on the current checked filters.
 * Checked values within a group are combined with OR; groups with AND.
 *
 * @param {Iterable} filters - iterable of filter sections
 * @param {number} [excludedFilterId]
 * @returns {Array[]}
 */
export function computeFilterDomain(filters, excludedFilterId) {
    const domain = [];

    function addCondition(fieldName, valueMap) {
        const ids = [];
        for (const [valueId, value] of valueMap) {
            if (value.checked) {
                ids.push(valueId);
            }
        }
        if (ids.length) {
            domain.push([fieldName, "in", ids]);
        }
    }

    for (const filter of filters) {
        if (filter.id === excludedFilterId) {
            continue;
        }
        const { fieldName, groups, values } = filter;
        if (groups) {
            for (const group of groups.values()) {
                addCondition(fieldName, group.values);
            }
        } else {
            addCondition(fieldName, values);
        }
    }
    return domain;
}

/**
 * Compute a domain/object of domains to complement filter domains for accurate
 * record counts (by group). Checked values within a group should not impact
 * counts for other values in the same group.
 *
 * @param {Object} filter
 * @param {Object} searchViewFields
 * @returns {Object|Array[]|null}
 */
export function computeGroupDomain(filter, searchViewFields) {
    const { fieldName, groups, enableCounters } = filter;
    const { type: fieldType } = searchViewFields[fieldName];

    if (!enableCounters || !groups) {
        return { many2one: [], many2many: {} }[fieldType];
    }

    let groupDomain = null;
    if (fieldType === "many2one") {
        for (const group of groups.values()) {
            const valueIds = [];
            let active = false;
            for (const [valueId, value] of group.values) {
                valueIds.push(valueId);
                if (value.checked) {
                    active = true;
                }
            }
            if (active) {
                if (groupDomain) {
                    groupDomain = [[0, "=", 1]];
                    break;
                } else {
                    groupDomain = [[fieldName, "in", valueIds]];
                }
            }
        }
    } else if (fieldType === "many2many") {
        const checkedValueIds = new Map();
        groups.forEach(({ values }, groupId) => {
            values.forEach(({ checked }, valueId) => {
                if (checked) {
                    if (!checkedValueIds.has(groupId)) {
                        checkedValueIds.set(groupId, []);
                    }
                    /** @type {any[]} */ (checkedValueIds.get(groupId)).push(valueId);
                }
            });
        });
        groupDomain = {};
        for (const [gId, ids] of checkedValueIds.entries()) {
            for (const groupId of groups.keys()) {
                if (gId !== groupId) {
                    const key = JSON.stringify(groupId);
                    if (!groupDomain[key]) {
                        groupDomain[key] = [];
                    }
                    /** @type {any[]} */ (groupDomain[key]).push([
                        fieldName,
                        "in",
                        ids,
                    ]);
                }
            }
        }
    }
    return groupDomain;
}

/**
 * Compute the domain for a field-type search item from its autocomplete values.
 *
 * @param {Object} field - the search item
 * @param {Object[]} autocompleteValues
 * @returns {Domain}
 */
export function computeFieldDomain(field, autocompleteValues) {
    const domains = autocompleteValues.map(({ label, value, operator }) => {
        let domain;
        if (field.filterDomain) {
            domain = new Domain(field.filterDomain).toList({
                self: label.trim(),
                raw_value: value,
            });
        } else if (field.type === "field") {
            domain = [[field.fieldName, operator, value]];
        } else if (field.type === "field_property") {
            domain = [
                field.propertyDomain,
                [
                    `${field.fieldName}.${field.propertyFieldDefinition.name}`,
                    operator,
                    value,
                ],
            ];
        }
        return new Domain(domain);
    });
    return Domain.or(domains);
}

/**
 * Compute the domain (or description) for a date filter from its generator ids.
 *
 * @param {Object} referenceMoment - luxon DateTime
 * @param {Object} dateFilter - the search item
 * @param {Array} generatorIds
 * @param {string} [key="domain"] - "domain" or "description"
 * @returns {Domain|string}
 */
export function computeDateFilterDomain(
    referenceMoment,
    dateFilter,
    generatorIds,
    key = "domain",
) {
    const dateFilterRange = constructDateDomain(
        referenceMoment,
        dateFilter,
        generatorIds,
    );
    return dateFilterRange[key];
}

/**
 * Compute the domain for a single active search item.
 *
 * @param {Object} activeItem
 * @param {Object} searchItems
 * @param {Object} referenceMoment
 * @returns {Domain|string|null}
 */
export function computeSearchItemDomain(activeItem, searchItems, referenceMoment) {
    const { searchItemId } = activeItem;
    const searchItem = searchItems[searchItemId];
    switch (searchItem.type) {
        case "field_property":
        case "field":
            return computeFieldDomain(searchItem, activeItem.autocompleteValues);
        case "dateFilter":
            return computeDateFilterDomain(
                referenceMoment,
                searchItem,
                activeItem.generatorIds,
            );
        case "filter":
        case "favorite":
            return searchItem.domain;
        default:
            return null;
    }
}

/**
 * Compute the combined search panel domain (categories AND filters).
 *
 * @param {Array[]} categoryDomain
 * @param {Array[]} filterDomain
 * @returns {Domain}
 */
export function computeSearchPanelDomain(categoryDomain, filterDomain) {
    return Domain.and(/** @type {any} */ ([categoryDomain, filterDomain]));
}

/**
 * Compute the full search domain by combining global, per-group, and search panel domains.
 *
 * @param {Object} params
 * @param {Object[]} params.groups - active query groups
 * @param {Domain|Array} params.globalDomain
 * @param {boolean} params.withGlobal
 * @param {boolean} params.withSearchPanel
 * @param {Function} params.getSearchItemDomain - (activeItem) => Domain|null
 * @param {Function} params.getSearchPanelDomain - () => Domain
 * @param {Object} params.domainEvalContext
 * @param {boolean} params.raw
 * @returns {any[]|Domain}
 */
export function computeDomain({
    groups,
    globalDomain,
    withGlobal,
    withSearchPanel,
    getSearchItemDomain,
    getSearchPanelDomain,
    domainEvalContext,
    raw,
}) {
    const domains = [];
    if (withGlobal) {
        domains.push(globalDomain);
    }
    for (const group of groups) {
        const groupActiveItemDomains = [];
        for (const activeItem of group.activeItems) {
            const domain = getSearchItemDomain(activeItem);
            if (domain) {
                groupActiveItemDomains.push(domain);
            }
        }
        const groupDomain = Domain.or(groupActiveItemDomains);
        domains.push(groupDomain);
    }
    if (withSearchPanel) {
        domains.push(getSearchPanelDomain());
    }
    const domain = Domain.and(domains);
    return raw ? domain : domain.toList(domainEvalContext);
}
