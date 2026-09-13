// @ts-check
/** @odoo-module native */

import { makeLogger } from "@web/core/debug/debug_logger";

const log = makeLogger("web.search.panel.tree");

/**
 * Break one parent edge per cycle before building children. Every row then has
 * a finite path to a root, even for custom server payloads with cyclic parents.
 * @param {Map<any, any>} values
 */
function normalizeCategoryParents(values) {
    const resolved = new Set([false]);
    for (const id of values.keys()) {
        const path = new Set();
        let current = id;
        while (current && !resolved.has(current)) {
            const value = values.get(current);
            if (path.has(current)) {
                log.logic("parent-cycle", () => ({
                    id: current,
                    parentId: value.parentId,
                }));
                value.parentId = false;
                break;
            }
            path.add(current);
            if (!values.has(value.parentId)) {
                value.parentId = false;
            }
            current = value.parentId;
        }
        for (const pathId of path) {
            resolved.add(pathId);
        }
    }
}

/**
 * @param {any[]} groupIds
 * @param {Map<any, {name: string, sequence?: number}>} groups
 * @returns {any[]}
 */
function sortGroupIds(groupIds, groups) {
    /**
     * @param {any} id
     * @returns {[number, string]}
     */
    const rank = (id) => {
        const { sequence, name } = groups.get(id) ?? {};
        return [
            typeof sequence === "number" ? sequence : Number.POSITIVE_INFINITY,
            String(name ?? ""),
        ];
    };
    return [...groupIds].sort((a, b) => {
        const [sequenceA, nameA] = rank(a);
        const [sequenceB, nameB] = rank(b);
        if (sequenceA !== sequenceB) {
            return sequenceA - sequenceB;
        }
        return nameA.localeCompare(nameB);
    });
}

/**
 * @param {Record<string, any>} category
 * @param {Record<string, any>} result
 * @param {Function} ensureCategoryValue
 */
export function createCategoryTree(category, result, ensureCategoryValue) {
    const { error_msg, parent_field: parentField } = result;
    let { values } = result;
    if (error_msg) {
        category.errorMsg = error_msg;
        values = [];
    } else {
        delete category.errorMsg;
    }
    if (category.hierarchize) {
        category.parentField = parentField;
    }
    const allRoot = category.values.get(false);
    category.values = new Map();
    if (allRoot) {
        allRoot.childrenIds = [];
        category.values.set(false, allRoot);
    }
    for (const value of values) {
        category.values.set(value.id, {
            ...value,
            childrenIds: [],
            parentId: category.hierarchize ? value[parentField] || false : false,
        });
    }
    normalizeCategoryParents(category.values);
    for (const value of values) {
        const { parentId } = category.values.get(value.id);
        if (parentId && category.values.has(parentId)) {
            category.values.get(parentId).childrenIds.push(value.id);
        }
    }
    category.rootIds = [false];
    for (const value of values) {
        const { parentId } = category.values.get(value.id);
        if (!parentId || !category.values.has(parentId)) {
            category.rootIds.push(value.id);
        }
    }
    const valueIds = [false, ...values.map((/** @type {any} */ val) => val.id)];
    ensureCategoryValue(category, valueIds);
}

/**
 * @param {Record<string, any>} filter
 * @param {Record<string, any>} result
 */
export function createFilterTree(filter, result) {
    const { error_msg } = result;
    let { values } = result;
    if (error_msg) {
        filter.errorMsg = error_msg;
        values = [];
    } else {
        delete filter.errorMsg;
    }

    values = values.map((/** @type {any} */ value) => ({
        ...value,
        checked: filter.values.get(value.id)?.checked ?? false,
    }));

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
            }
            groups.get(groupId).values.set(value.id, value);
        }
        filter.groups = groups;
        filter.sortedGroupIds = sortGroupIds(groupIds, groups);
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
