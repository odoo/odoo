// @ts-check
/** @odoo-module native */

import { evaluateBooleanExpr } from "@web/core/py_js/py";

/** @import { DomainListRepr } from "@web/core/domain" */
export const SPECIAL = Symbol("special");

/**
 * @template T
 * @param {T} value
 * @returns {T | undefined}
 */
function toWire(value) {
    const json = JSON.stringify(value);
    return json === undefined ? /** @type {T} */ (undefined) : JSON.parse(json);
}

export const SEARCH_MODEL_STATE_VERSION = 3;

export const FAVORITE_PRIVATE_GROUP = 1;
export const FAVORITE_SHARED_GROUP = 2;

/**
 * @param {Record<string, any>} section
 * @returns {boolean}
 */
export function hasValues(section) {
    const { errorMsg, type, values } = section;
    if (errorMsg) {
        return true;
    }
    switch (type) {
        case "category": {
            return values?.size > 1;
        }
        case "filter": {
            return values?.size > 0;
        }
        default: {
            return false;
        }
    }
}

/**
 * @param {string | undefined} expr
 * @param {Record<string, any>} evalContext
 * @returns {boolean}
 */
export function isInvisible(expr, evalContext) {
    try {
        return evaluateBooleanExpr(expr, evalContext);
    } catch (error) {
        console.warn(`[search] ignoring invisible="${expr}": ${error.message}`);
        return false;
    }
}

/**
 * @param {Map<any, Record<string, any>>} map
 * @returns {any[][]}
 */
function mapToArray(map) {
    const result = [];
    for (const [key, val] of map) {
        const valCopy = { ...val };
        result.push([key, valCopy]);
    }
    return result;
}

/**
 * @param {[any, Record<string, any>][]} array
 * @returns {Map<any, Record<string, any>>}
 */
function arrayToMap(array) {
    return new Map(array.map(([key, val]) => [key, { ...val }]));
}

/**
 * @typedef {Object} SearchModelState
 * @property {number} [version]
 * @property {Record<string, any>[]} query
 * @property {string|false} orderByCount
 * @property {boolean} defaultGroupByRemoved
 * @property {Record<number, Object>} searchItems
 * @property {number} nextId
 * @property {number} nextGroupId
 * @property {number} nextGroupNumber
 * @property {Record<string, any>} [searchPanelInfo]
 * @property {[number, Record<string, any>][]} sections
 * @property {DomainListRepr} [searchDomain]
 * @property {Record<string, Object>} [propertySearchViewFields]
 */

/**
 * @param {Record<string, any>} source
 * @returns {Partial<SearchModelState>}
 */
export function queryToState(source) {
    return {
        query: toWire(source.query),
        orderByCount: source.orderByCount,
        defaultGroupByRemoved: source.defaultGroupByRemoved,
    };
}

/**
 * @param {Partial<SearchModelState>} state
 * @param {Record<string, any>} target
 */
export function queryFromState(state, target) {
    target.query = toWire(state.query ?? []);
    target.orderByCount = state.orderByCount ?? false;
    target.defaultGroupByRemoved = state.defaultGroupByRemoved ?? false;
}

/**
 * @param {Record<string, any>} source
 * @returns {Partial<SearchModelState>}
 */
export function itemsToState(source) {
    return {
        searchItems: toWire(source.searchItems),
        nextId: source.nextId,
        nextGroupId: source.nextGroupId,
        nextGroupNumber: source.nextGroupNumber,
    };
}

/**
 * @param {Partial<SearchModelState>} state
 * @param {Record<string, any>} target
 */
export function itemsFromState(state, target) {
    target.searchItems = toWire(state.searchItems ?? {});
    target.nextId = state.nextId;
    target.nextGroupId = state.nextGroupId;
    target.nextGroupNumber = state.nextGroupNumber;
}

/**
 * @param {Record<string, any>} source
 * @returns {Partial<SearchModelState>}
 */
export function panelToState(source) {
    /** @type {Partial<SearchModelState>} */
    const state = {
        searchPanelInfo: toWire(source.searchPanelInfo),
        sections: sectionsToState(source.sections),
    };
    if (source.searchDomain !== undefined) {
        state.searchDomain = toWire(source.searchDomain);
    }
    return state;
}

/**
 * @param {Partial<SearchModelState>} state
 * @param {Record<string, any>} target
 */
export function panelFromState(state, target) {
    target.searchPanelInfo = toWire(state.searchPanelInfo);
    target.sections = sectionsFromState(
        /** @type {[number, Record<string, any>][]} */ (state.sections),
    );
    if (state.searchDomain !== undefined) {
        target.searchDomain = toWire(state.searchDomain);
    }
}

/**
 * @param {Map<number, Record<string, any>>} sections
 * @returns {[number, Record<string, any>][]}
 */
function sectionsToState(sections) {
    const result = /** @type {[number, Record<string, any>][]} */ (
        mapToArray(sections)
    );
    for (const [, section] of result) {
        section.values = mapToArray(section.values);
        if (section.groups) {
            section.groups = mapToArray(section.groups);
            for (const [, group] of section.groups) {
                group.valueIds = [...group.values.keys()];
                delete group.values;
            }
        }
    }
    return toWire(result);
}

/**
 * @param {[number, Record<string, any>][]} sections
 * @returns {Map<number, Record<string, any>>}
 */
function sectionsFromState(sections) {
    const result = arrayToMap(toWire(sections));
    for (const [, section] of result) {
        section.values = arrayToMap(section.values);
        if (section.groups) {
            section.groups = arrayToMap(section.groups);
            for (const [, group] of section.groups) {
                const valueIds =
                    group.valueIds ??
                    (group.values || []).map(
                        (/** @type {any[]} */ [valueId]) => valueId,
                    );
                delete group.valueIds;
                group.values = new Map();
                for (const valueId of valueIds) {
                    const value = section.values.get(valueId);
                    if (value) {
                        group.values.set(valueId, value);
                    }
                }
            }
        }
    }
    return result;
}

/**
 * @param {Record<string, any>} source
 * @returns {Partial<SearchModelState>}
 */
export function propertiesToState(source) {
    /** @type {Record<string, Object>} */
    const propertySearchViewFields = {};
    for (const [name, field] of Object.entries(source.searchViewFields || {})) {
        if (field.relatedPropertyField) {
            propertySearchViewFields[name] = toWire(field);
        }
    }
    return { propertySearchViewFields };
}

/**
 * @param {Partial<SearchModelState>} state
 * @param {Record<string, any>} target
 */
export function propertiesFromState(state, target) {
    if (!state.propertySearchViewFields) {
        return;
    }
    target.searchViewFields ||= {};
    for (const [name, field] of Object.entries(
        /** @type {Record<string, Record<string, any>>} */ (
            state.propertySearchViewFields
        ),
    )) {
        if (name in target.searchViewFields) {
            continue;
        }
        const copy = toWire(field);
        if (!copy) {
            continue;
        }
        const parent = target.searchViewFields[copy.relatedPropertyField?.name];
        if (parent) {
            copy.relatedPropertyField = parent;
        }
        target.searchViewFields[name] = copy;
    }
}

/**
 * @param {Record<string, any>} globalContext
 * @returns {{ searchDefaults: Object, searchPanelDefaults: Object }}
 */
export function takeSearchDefaults(globalContext) {
    /** @type {Record<string, any>} */
    const searchDefaults = {};
    /** @type {Record<string, any>} */
    const searchPanelDefaults = {};
    for (const key of Object.keys(globalContext)) {
        const defaultValue = globalContext[key];
        const searchDefaultMatch = /^search_default_(.*)$/.exec(key);
        if (searchDefaultMatch) {
            if (defaultValue) {
                searchDefaults[searchDefaultMatch[1]] = defaultValue;
            }
            delete globalContext[key];
            continue;
        }
        const searchPanelDefaultMatch = /^searchpanel_default_(.*)$/.exec(key);
        if (searchPanelDefaultMatch) {
            searchPanelDefaults[searchPanelDefaultMatch[1]] = defaultValue;
            delete globalContext[key];
        }
    }
    return { searchDefaults, searchPanelDefaults };
}
