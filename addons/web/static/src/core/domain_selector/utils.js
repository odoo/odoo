/** @odoo-module **/

import { Domain } from "@web/core/domain";
import { getDefaultFieldValue, getDefaultOperator } from "./domain_selector_fields";
import { useService } from "@web/core/utils/hooks";
import { Expression, toValue, toDomain, toTree } from "@web/core/domain_tree";

/**
 * @param {import("@web/core/domain_tree").Tree} tree
 * @param {Function} getFieldDef
 * @returns {import("@web/core/domain_tree").Tree}
 */
export function createVirtualOperators(tree, getFieldDef) {
    if (tree.type === "condition") {
        const { path, operator, value } = tree;
        if (["=", "!="].includes(operator)) {
            const fieldDef = getFieldDef(path);
            if (fieldDef?.type === "boolean") {
                return { ...tree, operator: operator === "=" ? "is" : "is_not" };
            } else if (value === false) {
                return { ...tree, operator: operator === "=" ? "not_set" : "set" };
            }
        }
        return tree;
    }
    const processedChildren = tree.children.map((c) => createVirtualOperators(c, getFieldDef));
    return { ...tree, children: processedChildren };
}

/**
 * @param {import("@web/core/domain_tree").Tree} tree
 * @returns {import("@web/core/domain_tree").Tree}
 */
function removeVirtualOperators(tree) {
    if (tree.type === "condition") {
        const { operator } = tree;
        if (["is", "is_not"].includes(operator)) {
            return { ...tree, operator: operator === "is" ? "=" : "!=" };
        }
        if (["set", "not_set"].includes(operator)) {
            return { ...tree, operator: operator === "set" ? "!=" : "=" };
        }
        return tree;
    }
    const processedChildren = tree.children.map((c) => removeVirtualOperators(c));
    return { ...tree, children: processedChildren };
}

/**
 * @param {import("@web/core/domain_tree").Tree} domainSelectorTree
 * @returns {string}
 */
export function buildDomain(domainSelectorTree) {
    const tree = removeVirtualOperators(domainSelectorTree);
    return toDomain(tree);
}

/**
 * @param {import("@web/core/domain").DomainRepr} domain
 * @param {Function} getFieldDef
 * @param {Object} [options={}]
 * @returns {import("@web/core/domain_tree").Tree}
 */
export function buildDomainSelectorTree(domain, getFieldDef, options = {}) {
    const tree = toTree(domain, options);
    return createVirtualOperators(tree, getFieldDef);
}

/**
 * @param {import("@web/core/domain_tree").Value} value
 * @returns {import("@web/core/domain_tree").Value}
 */
function cloneValue(value) {
    if (value instanceof Expression) {
        return new Expression(value.toAST());
    }
    if (Array.isArray(value)) {
        return value.map((val) => cloneValue(val));
    }
    return value;
}

/**
 * @param {import("@web/core/domain_tree").Tree} tree
 * @returns {import("@web/core/domain_tree").Tree}
 */
export function cloneTree(tree) {
    const clone = {};
    for (const key in tree) {
        clone[key] = cloneValue(tree[key]);
    }
    return clone;
}

/**
 * @param {import("@web/core/domain").DomainRepr} domain
 * @returns {import("@web/core/domain_tree").Value[]}
 */
export function extractPathsFromDomain(domain) {
    domain = new Domain(domain);
    const paths = new Set();
    for (const node of domain.ast.value) {
        if ([4, 10].includes(node.type)) {
            paths.add(toValue(node.value[0]));
        }
    }
    return [...paths];
}

const SPECIAL_FIELDS = ["country_id", "user_id", "partner_id", "stage_id"];

function getDefaultDomain(fieldDefs) {
    let fieldDef = null;
    for (const name of SPECIAL_FIELDS) {
        fieldDef = fieldDefs[name];
        if (fieldDef) {
            const operatorInfo = getDefaultOperator(fieldDef);
            const value = getDefaultFieldValue(fieldDef, operatorInfo.operator);
            return buildDomain({
                type: "condition",
                negate: false,
                path: fieldDef.name,
                operator: operatorInfo.operator,
                value,
            });
        }
    }
    return new Domain([["id", "=", 1]]).toString();
}

export function useGetDefaultLeafDomain() {
    const fieldService = useService("field");
    return async (resModel) => {
        const fieldDefs = await fieldService.loadFields(resModel);
        return getDefaultDomain(fieldDefs);
    };
}
