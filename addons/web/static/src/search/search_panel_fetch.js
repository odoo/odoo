// @ts-check

/** @module search/search_panel_fetch - Search panel section tree creation utilities */

/**
 * Create the category tree from server results.
 *
 * @param {Object} category - the category section (mutated in place)
 * @param {Object} result - server response from search_panel_select_range
 * @param {Function} ensureCategoryValue - (category, valueIds) => void
 */

import { sortBy } from "@web/core/utils/collections/arrays";
export function createCategoryTree(category, result, ensureCategoryValue) {
    const { error_msg, parent_field: parentField } = result;
    let { values } = result;
    if (error_msg) {
        category.errorMsg = error_msg;
        values = [];
    }
    if (category.hierarchize) {
        category.parentField = parentField;
    }
    for (const value of values) {
        category.values.set(value.id, {
            ...value,
            childrenIds: [],
            parentId: value[parentField] || false,
        });
    }
    for (const value of values) {
        const { parentId } = category.values.get(value.id);
        if (parentId && category.values.has(parentId)) {
            category.values.get(parentId).childrenIds.push(value.id);
        }
    }
    // collect rootIds
    category.rootIds = [false];
    for (const value of values) {
        const { parentId } = category.values.get(value.id);
        if (!parentId) {
            category.rootIds.push(value.id);
        }
    }
    // Set active value from context
    const valueIds = [false, ...values.map((val) => val.id)];
    ensureCategoryValue(category, valueIds);
}

/**
 * Create the filter tree from server results.
 *
 * @param {Object} filter - the filter section (mutated in place)
 * @param {Object} result - server response from search_panel_select_multi_range
 */
export function createFilterTree(filter, result) {
    const { error_msg } = result;
    let { values } = result;
    if (error_msg) {
        filter.errorMsg = error_msg;
        values = [];
    }

    // restore checked property
    values.forEach((value) => {
        const oldValue = filter.values.get(value.id);
        value.checked = oldValue ? oldValue.checked : false;
    });

    filter.values = new Map();
    const groupIds = [];
    if (filter.groupBy) {
        const groups = new Map();
        for (const value of values) {
            const groupId = value.group_id;
            if (!groups.has(groupId)) {
                if (groupId) {
                    groupIds.push(groupId);
                }
                groups.set(groupId, {
                    id: groupId,
                    name: value.group_name,
                    values: new Map(),
                    tooltip: value.group_tooltip,
                    sequence: value.group_sequence,
                    color_index: value.color_index,
                });
                // restore former checked state
                const oldGroup = filter.groups && filter.groups.get(groupId);
                groups.get(groupId).state = (oldGroup && oldGroup.state) || false;
            }
            groups.get(groupId).values.set(value.id, value);
        }
        filter.groups = groups;
        filter.sortedGroupIds = sortBy(
            groupIds,
            (id) => groups.get(id).sequence || groups.get(id).name,
        );
        for (const group of filter.groups.values()) {
            for (const [valueId, value] of group.values) {
                filter.values.set(valueId, value);
            }
        }
    } else {
        for (const value of values) {
            filter.values.set(value.id, value);
        }
    }
}
