// @ts-check

/** @module @web/components/domain_selector/utils - Default condition and domain builders for the domain selector */

import { getDomainDisplayedOperators } from "@web/components/domain_selector/domain_selector_operator_editor";
import { condition } from "@web/components/tree_editor/condition_tree";
import { domainFromTree } from "@web/components/tree_editor/domain_from_tree";
import { getDefaultValue } from "@web/components/tree_editor/tree_editor_value_editors";
import { getDefaultPath } from "@web/components/tree_editor/utils";
import { useService } from "@web/core/utils/hooks";
/**
 * @param {Record<string, Object>} fieldDefs - map of field name to field definition
 * @returns {Object} a condition node with the default path, operator, and value
 */
export function getDefaultCondition(fieldDefs) {
    const defaultPath = getDefaultPath(fieldDefs);
    const fieldDef = fieldDefs[defaultPath];
    const operator = getDomainDisplayedOperators(fieldDef)[0];
    const value = getDefaultValue(fieldDef, operator);
    return condition(fieldDef.name, operator, value);
}

/**
 * @param {Record<string, Object>} fieldDefs - map of field name to field definition
 * @returns {string} serialized domain string for the default condition
 */
export function getDefaultDomain(fieldDefs) {
    return domainFromTree(getDefaultCondition(fieldDefs));
}

/**
 * @returns {(resModel: string) => Promise<string>} async function that loads fields and returns the default domain
 */
export function useGetDefaultLeafDomain() {
    const fieldService = useService("field");
    return async (resModel) => {
        const fieldDefs = await fieldService.loadFields(resModel);
        return getDefaultDomain(fieldDefs);
    };
}
