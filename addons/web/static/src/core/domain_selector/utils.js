/** @odoo-module **/

import { Domain } from "@web/core/domain";
import { getDefaultValue, getDefaultOperator } from "./domain_selector_fields";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { unique, zip } from "@web/core/utils/arrays";
import { sprintf } from "@web/core/utils/strings";
import {
    Expression,
    toValue,
    toDomain,
    toTree,
    normalizeValue,
    formatValue as toSring,
} from "@web/core/domain_tree";
import { useLoadFieldInfo, useLoadPathDescription } from "@web/core/model_field_selector/utils";
import { getOperatorInfo } from "@web/core/domain_selector/domain_selector_operators";
import {
    deserializeDate,
    deserializeDateTime,
    formatDate,
    formatDateTime,
} from "@web/core/l10n/dates";

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
            } else if (fieldDef?.type !== "many2one" && value === false) {
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

function isId(val) {
    return Number.isInteger(val) && val >= 1;
}

/**
 * @param {import("@web/core/domain").DomainRepr} domain
 * @param {Function} getFieldDef
 * @returns {Object}
 */
export function extractIdsFromDomain(domain, getFieldDef) {
    domain = new Domain(domain);
    const idsByModel = {};
    for (const node of domain.ast.value) {
        if ([4, 10].includes(node.type)) {
            const path = toValue(node.value[0]);
            const fieldDef = getFieldDef(path);
            if (["many2one", "many2many", "one2many"].includes(fieldDef?.type)) {
                const value = toValue(node.value[2]);
                const values = Array.isArray(value) ? value : [value];
                const ids = values.filter((val) => isId(val));
                const resModel = fieldDef.relation;
                if (ids.length) {
                    if (!idsByModel[resModel]) {
                        idsByModel[resModel] = [];
                    }
                    idsByModel[resModel].push(...ids);
                }
            }
        }
    }
    for (const resModel in idsByModel) {
        idsByModel[resModel] = unique(idsByModel[resModel]);
    }
    return idsByModel;
}

export function useLoadDisplayNames(nameService) {
    nameService ||= useService("name");
    return async (resIdsByModel) => {
        const proms = [];
        const resModels = [];
        for (const [resModel, resIds] of Object.entries(resIdsByModel)) {
            resModels.push(resModel);
            proms.push(nameService.loadDisplayNames(resModel, resIds));
        }
        return Object.fromEntries(zip(resModels, await Promise.all(proms)));
    };
}

/**
 * @param {import("@web/core/domain_tree").Value} val
 * @param {boolean} disambiguate
 * @param {Object|null} fieldDef
 * @param {Object} displayNames
 * @returns
 */
function formatValue(val, disambiguate, fieldDef, displayNames) {
    if (val instanceof Expression) {
        return val.toString();
    }
    if (displayNames && isId(val)) {
        if (typeof displayNames[val] === "string") {
            val = displayNames[val];
        } else {
            return sprintf(_t(`Inaccessible/missing record ID: %s`), val);
        }
    }
    if (fieldDef?.type === "selection") {
        const [, label] = (fieldDef.selection || []).find(([v]) => v === val) || [];
        if (label !== undefined) {
            val = label;
        }
    }
    if (fieldDef?.type === "datetime") {
        return formatDateTime(deserializeDateTime(val));
    }
    if (fieldDef?.type === "date") {
        return formatDate(deserializeDate(val));
    }
    if (disambiguate && typeof val === "string") {
        return JSON.stringify(val);
    }
    return val;
}

function disambiguate(value, displayNames) {
    if (!Array.isArray(value)) {
        return value === "";
    }
    let hasSomeString = false;
    let hasSomethingElse = false;
    for (const val of value) {
        if (val === "") {
            return true;
        }
        if (typeof val === "string" || (displayNames && isId(val))) {
            hasSomeString = true;
        } else {
            hasSomethingElse = true;
        }
    }
    return hasSomeString && hasSomethingElse;
}

export function leafToString(fieldDef, operatorInfo, value, displayNames) {
    const description = {
        operatorDescription: `${operatorInfo.label}`,
        valueDescription: null,
    };

    if (["set", "not_set"].includes(operatorInfo.operator)) {
        return description;
    }
    if (["is", "is_not"].includes(operatorInfo.operator)) {
        description.valueDescription = {
            values: [value ? _t("set") : _t("not set")],
            join: "",
            addParenthesis: false,
        };
        return description;
    }

    const dis = disambiguate(value, displayNames);
    const values = (Array.isArray(value) ? value : [value]).map((val) =>
        formatValue(val, dis, fieldDef, displayNames)
    );
    let join;
    let addParenthesis = Array.isArray(value);
    switch (operatorInfo.operator) {
        case "between":
            join = _t("and");
            addParenthesis = false;
            break;
        case "in":
        case "not in":
            join = ",";
            break;
        default:
            join = _t("or");
    }
    description.valueDescription = { values, join, addParenthesis };
    return description;
}

const SPECIAL_FIELDS = ["country_id", "user_id", "partner_id", "stage_id"];

function getDefaultDomain(fieldDefs) {
    let fieldDef = null;
    for (const name of SPECIAL_FIELDS) {
        fieldDef = fieldDefs[name];
        if (fieldDef) {
            const operator = getDefaultOperator(fieldDef);
            const value = getDefaultValue(fieldDef, operator);
            return buildDomain({
                type: "condition",
                negate: false,
                path: fieldDef.name,
                operator,
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

/**
 * @param {Tree} tree
 * @returns {tree}
 */
export function simplifyTree(tree, isRoot = true) {
    if (tree.type === "condition") {
        return tree;
    }
    const processedChildren = tree.children.map((c) => simplifyTree(c, false));
    if (tree.value === "&") {
        return { ...tree, children: processedChildren };
    }
    const children = [];
    const childrenByPath = {};
    for (const child of processedChildren) {
        if (
            child.type === "connector" ||
            typeof child.path !== "string" ||
            !["=", "in"].includes(child.operator)
        ) {
            children.push(child);
        } else {
            if (!childrenByPath[child.path]) {
                childrenByPath[child.path] = [];
            }
            childrenByPath[child.path].push(child);
        }
    }
    for (const path in childrenByPath) {
        if (childrenByPath[path].length === 1) {
            children.push(childrenByPath[path][0]);
            continue;
        }
        const value = [];
        for (const child of childrenByPath[path]) {
            if (child.operator === "=") {
                value.push(child.value);
            } else {
                value.push(...child.value);
            }
        }
        children.push({
            type: "condition",
            negate: false,
            operator: "in",
            path: path,
            value: normalizeValue(value),
        });
    }
    if (children.length === 1 && !isRoot) {
        return { ...children[0] };
    }
    return { ...tree, children };
}

/**
 * @param {Tree} tree
 * @param {Function} getDescription
 * @param {boolean} [isSubExpression=true]
 * @returns {string}
 */
export function getDomainTreeDescription(
    tree,
    getFieldDef,
    getDescription,
    displayNames,
    isSubExpression = true
) {
    if (tree.type === "connector") {
        // we assume that the domain tree is normalized (--> there is at least two children)
        const childDescriptions = tree.children.map((c) =>
            getDomainTreeDescription(c, getFieldDef, getDescription, displayNames)
        );
        const separator = tree.value === "&" ? _t("and") : _t("or");
        let description = childDescriptions.join(` ${separator} `);
        if (isSubExpression || tree.negate) {
            description = `( ${description} )`;
        }
        if (tree.negate) {
            description = `! ${description}`;
        }
        return description;
    }
    const { negate, operator, path, value } = tree;
    const fieldDef = getFieldDef(path);
    const operatorInfo = getOperatorInfo(operator, negate);
    const { operatorDescription, valueDescription } = leafToString(
        fieldDef,
        operatorInfo,
        value,
        displayNames[fieldDef?.relation]
    );
    let description = `${getDescription(path)} ${operatorDescription} `;
    if (valueDescription) {
        const { values, join, addParenthesis } = valueDescription;
        const jointedValues = values.join(` ${join} `);
        description += addParenthesis ? `( ${jointedValues} )` : jointedValues;
    }
    return description;
}

export function useGetDomainTreeDescription(fieldService, nameService) {
    fieldService ||= useService("field");
    nameService ||= useService("name");
    const loadFieldInfo = useLoadFieldInfo(fieldService);
    const loadPathDescription = useLoadPathDescription(fieldService);
    const loadDisplayNames = useLoadDisplayNames(nameService);
    return async (resModel, tree) => {
        tree = simplifyTree(tree);
        const domain = toDomain(tree);
        const paths = extractPathsFromDomain(domain);
        const promises = [];
        const pathFieldDefs = {};
        const pathDescriptions = {};
        for (const path of paths) {
            promises.push(
                loadPathDescription(resModel, path).then(({ displayNames }) => {
                    pathDescriptions[toSring(path)] = displayNames.join(" 🠒 ");
                }),
                loadFieldInfo(resModel, path).then(({ fieldDef }) => {
                    pathFieldDefs[toSring(path)] = fieldDef;
                })
            );
        }
        await Promise.all(promises);
        const getFieldDef = (path) => pathFieldDefs[toSring(path)];
        const getDescription = (path) => pathDescriptions[toSring(path)];
        const idsByModel = extractIdsFromDomain(domain, getFieldDef);
        const treeWithVirtualOperators = createVirtualOperators(tree, getFieldDef);
        const displayNames = await loadDisplayNames(idsByModel);
        return getDomainTreeDescription(
            treeWithVirtualOperators,
            getFieldDef,
            getDescription,
            displayNames,
            false
        );
    };
}
