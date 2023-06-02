/** @odoo-module **/

import { Domain } from "@web/core/domain";
import { getDefaultFieldValue, getDefaultOperator } from "./domain_selector_fields";
import { toDomain, toTree } from "@web/core/domain_tree";
import { toDomainSelectorTree } from "@web/core/domain_selector/domain_selector_nodes";
import { useService } from "@web/core/utils/hooks";

/**
 * @param {BranchDomainNode} domainSelectorTree
 * @returns {string}
 */
export function buildDomain(domainSelectorTree) {
    const tree = toTree(domainSelectorTree.toDomain());
    return toDomain(tree);
}

/**
 * @param {import("@web/core/domain").DomainRepr} domain
 * @param {Object} pathsInfo
 * @param {Object} options
 * @returns {BranchDomainNode}
 */
export function buildDomainSelectorTree(domain, pathsInfo, options = {}) {
    const tree = toTree(domain, options);
    return toDomainSelectorTree(tree, pathsInfo, options.previousTree);
}

/**
 * @param {import("@web/core/domain").DomainRepr} domain
 * @returns {any[]}
 */
export function extractPathsFromDomain(domain) {
    domain = new Domain(domain);
    const paths = new Set();
    for (const node of domain.ast.value) {
        if ([4, 10].includes(node.type)) {
            paths.add(node.value[0].value);
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
            const operator = getDefaultOperator(fieldDef);
            const defaultValue = getDefaultFieldValue(fieldDef);
            return new Domain([[fieldDef.name, operator, defaultValue]]).toString();
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
