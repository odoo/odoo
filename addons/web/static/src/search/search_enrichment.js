// @ts-check

/** @module @web/search/search_enrichment - Pure search-item enrichment producing activated copies with period/interval metadata */

/**
 * Pure search-item enrichment for SearchModel.
 *
 * Takes a search item and query state, returns an enriched copy with
 * activation status, period options, interval options, or autocomplete
 * values attached — without mutating any state.
 */

import { getPeriodOptions } from "./utils/dates";

/**
 * Enrich option descriptors with an `isActive` flag.
 *
 * @param {Object[]} options
 * @param {Array} selectedIds - currently selected option ids
 * @returns {Object[]}
 */
function enrichOptions(options, selectedIds) {
    return options.map((o) => {
        const { description, id, groupNumber } = o;
        const isActive = selectedIds.some((optionId) => optionId === id);
        return { description, id, groupNumber, isActive };
    });
}

/**
 * Return an enriched copy of `searchItem` with activation status and
 * type-specific metadata (options, autocomplete values).
 *
 * Returns `null` if the item should be hidden.
 *
 * @param {Object} searchItem
 * @param {Object[]} query - current query elements
 * @param {import("luxon").DateTime} referenceMoment
 * @param {Object[]} intervalOptions
 * @returns {Object | null}
 */
export function enrichSearchItem(searchItem, query, referenceMoment, intervalOptions) {
    if (searchItem.type === "field" && searchItem.fieldType === "properties") {
        return { ...searchItem };
    }
    const queryElements = query.filter(
        (queryElem) => queryElem.searchItemId === searchItem.id,
    );
    const isActive = Boolean(queryElements.length);
    const enrichedSearchItem = Object.assign({ isActive }, searchItem);
    switch (searchItem.type) {
        case "dateFilter":
            enrichedSearchItem.options = enrichOptions(
                getPeriodOptions(referenceMoment, searchItem.optionsParams),
                queryElements.map((queryElem) => queryElem.generatorId),
            );
            break;
        case "dateGroupBy":
            enrichedSearchItem.options = enrichOptions(
                intervalOptions,
                queryElements.map((queryElem) => queryElem.intervalId),
            );
            break;
        case "field":
        case "field_property":
            enrichedSearchItem.autocompleteValues = queryElements.map(
                (queryElem) => queryElem.autocompleteValue,
            );
            break;
    }
    return enrichedSearchItem;
}
