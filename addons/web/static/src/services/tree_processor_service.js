// @ts-check

/** @module @web/services/tree_processor_service - Converts domains to condition trees with human-readable descriptions and tooltips */

/**
 * Format a condition value for display in domain descriptions.
 * Resolves record IDs to display names, selection labels, and date formatting.
 * @param {import("@web/components/tree_editor/condition_tree").Value} val
 * @param {boolean} disambiguate - whether to JSON-stringify string values
 * @param {Object | null} fieldDef - field definition from the field service
 * @param {Record<number, string>} displayNames - map of record IDs to display names
 * @returns {string | import("@web/components/tree_editor/condition_tree").Value}
 */
import {
    condition,
    Expression,
    isTree,
    normalizeValue,
} from "@web/components/tree_editor/condition_tree";
import { constructTreeFromDomain } from "@web/components/tree_editor/construct_tree_from_domain";
import { InRange } from "@web/components/tree_editor/tree_editor_components";
import { getOperatorLabel } from "@web/components/tree_editor/tree_editor_operator_editor";
import { disambiguate, getResModel, isId } from "@web/components/tree_editor/utils";
import { introduceVirtualOperators } from "@web/components/tree_editor/virtual_operators";
import {
    deserializeDate,
    deserializeDateTime,
    formatDate,
    formatDateTime,
} from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { unique, zip } from "@web/core/utils/collections/arrays";

function formatValue(val, disambiguate, fieldDef, displayNames) {
    if (val instanceof Expression) {
        return val.toString();
    }
    if (displayNames && isId(val)) {
        if (typeof displayNames[/** @type {any} */ (val)] === "string") {
            val = displayNames[/** @type {any} */ (val)];
        } else {
            return _t("Inaccessible/missing record ID: %s", val);
        }
    }
    if (fieldDef?.type === "selection") {
        const [, label] = (fieldDef.selection || []).find(([v]) => v === val) || [];
        if (label !== undefined) {
            val = label;
        }
    }
    if (typeof val === "string") {
        if (fieldDef?.type === "datetime") {
            return formatDateTime(deserializeDateTime(val));
        }
        if (fieldDef?.type === "date") {
            return formatDate(deserializeDate(val));
        }
    }
    if (disambiguate && typeof val === "string") {
        return JSON.stringify(val);
    }
    return val;
}

/**
 * Collect all field paths referenced in a condition tree.
 * @param {any} tree
 * @param {boolean} [lookInSubTrees=false] - whether to recurse into sub-expression trees
 * @returns {any[]} unique field paths found in the tree
 */
function getPathsInTree(tree, lookInSubTrees = false) {
    const paths = [];
    if (tree.type === "condition") {
        paths.push(tree.path);
        if (typeof tree.path === "string" && lookInSubTrees && isTree(tree.value)) {
            const subTreePaths = getPathsInTree(tree.value, lookInSubTrees);
            for (const p of subTreePaths) {
                if (typeof p === "string") {
                    paths.push(`${tree.path}.${p}`);
                }
            }
        }
    }
    if (tree.type === "connector" && tree.children) {
        for (const child of tree.children) {
            paths.push(...getPathsInTree(child, lookInSubTrees));
        }
    }
    return unique(paths);
}

/**
 * Simplify a condition tree by merging multiple `=` / `in` conditions on the
 * same field path (under OR connectors) into a single `in` condition.
 * @param {any} tree
 * @returns {any}
 */
function simplifyTree(tree) {
    if (tree.type === "condition") {
        return tree;
    }
    const processedChildren = tree.children.map(simplifyTree);
    if (tree.value === "&") {
        return { ...tree, children: processedChildren };
    }
    const children = [];
    const childrenByPath = {};
    for (let index = 0; index < processedChildren.length; index++) {
        const child = processedChildren[index];
        if (
            child.type === "connector" ||
            typeof child.path !== "string" ||
            !["=", "in"].includes(child.operator)
        ) {
            children.push(child);
        } else {
            if (!childrenByPath[child.path]) {
                childrenByPath[child.path] = { elems: [], index };
                children.push(child); // will be replaced if necessary
            }
            childrenByPath[child.path].elems.push(child);
        }
    }
    for (const path in childrenByPath) {
        if (childrenByPath[path].elems.length === 1) {
            continue;
        }
        const value = [];
        for (const child of childrenByPath[path].elems) {
            if (child.operator === "=") {
                value.push(child.value);
            } else {
                value.push(...child.value);
            }
        }
        children[childrenByPath[path].index] = condition(
            path,
            "in",
            normalizeValue(unique(value)),
        );
    }
    if (children.length === 1) {
        return { ...children[0] };
    }
    return { ...tree, children };
}

/**
 * Recursively extract record IDs from relational conditions in a tree.
 * @param {any} tree
 * @param {(path: string) => Object | null} getFieldDef
 * @param {Record<string, number[]>} idsByModel - accumulator, mutated in place
 * @returns {Record<string, number[]>} the same idsByModel accumulator
 */
function _extractIdsRecursive(tree, getFieldDef, idsByModel) {
    if (tree.type === "condition") {
        const fieldDef = getFieldDef(tree.path);
        if (["many2one", "many2many", "one2many"].includes(fieldDef?.type)) {
            const value = tree.value;
            const values = Array.isArray(value) ? value : [value];
            const ids = values.filter((val) => isId(val));
            const resModel = getResModel(fieldDef);
            if (ids.length) {
                if (!idsByModel[resModel]) {
                    idsByModel[resModel] = [];
                }
                idsByModel[resModel].push(...ids);
            }
        }
    }
    if (tree.type === "connector") {
        for (const child of tree.children) {
            _extractIdsRecursive(child, getFieldDef, idsByModel);
        }
    }
    return idsByModel;
}

/**
 * Extract all record IDs from relational conditions, grouped by co-model.
 * @param {import("@web/components/tree_editor/condition_tree").Tree} tree
 * @param {(path: string) => Object | null} getFieldDef
 * @returns {Record<string, number[]>} map of model name to unique record IDs
 */
function extractIdsFromTree(tree, getFieldDef) {
    const idsByModel = _extractIdsRecursive(tree, getFieldDef, {});

    for (const resModel in idsByModel) {
        idsByModel[resModel] = unique(idsByModel[resModel]);
    }

    return idsByModel;
}

/**
 * @typedef {Object} TreeProcessorServiceAPI
 * @property {(resModel: string, tree: import("@web/components/tree_editor/condition_tree").Tree, isSubExpression?: boolean, limit?: number, pathLimit?: number) => Promise<string>} getDomainTreeDescription
 * @property {(resModel: string, tree: import("@web/components/tree_editor/condition_tree").Tree) => Promise<string>} getDomainTreeTooltip
 * @property {(resModel: string, tree: import("@web/components/tree_editor/condition_tree").Tree, limit?: number, pathLimit?: number) => Promise<(node: any) => ConditionDescription>} makeGetConditionDescription
 * @property {(resModel: string, tree: import("@web/components/tree_editor/condition_tree").Tree) => Promise<(path: string) => Object | null>} makeGetFieldDef
 * @property {(resModel: string, domain: any[], distributeNot?: boolean) => Promise<import("@web/components/tree_editor/condition_tree").Tree>} treeFromDomain
 */

/**
 * @typedef {Object} ConditionDescription
 * @property {string} pathDescription - human-readable field path
 * @property {string} operatorDescription - operator label
 * @property {{ values: any[], join: string, addParenthesis: boolean } | null} valueDescription
 */

/**
 * Service for processing domain condition trees: converting domains to trees,
 * generating human-readable descriptions and tooltips, and resolving field
 * definitions and display names.
 */
export const treeProcessorService = {
    dependencies: ["field", "name"],
    async: [
        "getDomainTreeDescription",
        "getDomainTreeTooltip",
        "makeGetConditionDescription",
        "makeGetFieldDef",
        "treeFromDomain",
    ],
    /**
     * @param {import("@web/env").OdooEnv} _env
     * @param {{ field: any, name: any }} services
     * @returns {TreeProcessorServiceAPI}
     */
    start(_env, { field: fieldService, name: nameService }) {
        /**
         * Load display names for all relational record IDs in a tree.
         * @param {import("@web/components/tree_editor/condition_tree").Tree} tree
         * @param {(path: string) => Object | null} getFieldDef
         * @returns {Promise<Record<string, Record<number, string>>>} map of model to (id → displayName)
         */
        async function getDisplayNames(tree, getFieldDef) {
            const resIdsByModel = extractIdsFromTree(tree, getFieldDef);
            const proms = [];
            const resModels = [];
            for (const [resModel, resIds] of Object.entries(resIdsByModel)) {
                resModels.push(resModel);
                proms.push(nameService.loadDisplayNames(resModel, resIds));
            }
            return Object.fromEntries(zip(resModels, await Promise.all(proms)));
        }

        /**
         * Build a lookup function that maps field paths to human-readable descriptions.
         * @param {string} resModel
         * @param {import("@web/components/tree_editor/condition_tree").Tree} tree
         * @param {number} [limit] - max segments in path description before truncating
         * @returns {Promise<(path: string) => string | undefined>}
         */
        async function makeGetPathDescriptions(resModel, tree, limit) {
            const paths = getPathsInTree(tree);
            const promises = [];
            const pathDescriptions = new Map();
            for (const path of paths) {
                promises.push(
                    fieldService
                        .loadPathDescription(resModel, path)
                        .then(({ displayNames }) => {
                            pathDescriptions.set(
                                path,
                                `${displayNames.slice(0, limit).join(" \u2794 ")}${
                                    displayNames.length > limit ? "..." : ""
                                }`,
                            );
                        }),
                );
            }
            await Promise.all(promises);
            return (path) => pathDescriptions.get(path);
        }

        /**
         * Create a function that returns a structured description for a condition node.
         * @param {string} resModel
         * @param {import("@web/components/tree_editor/condition_tree").Tree} tree
         * @param {number} [limit] - max values to show before truncating
         * @param {number} [pathLimit] - max segments in path descriptions
         * @returns {Promise<(node: any) => ConditionDescription>}
         */
        async function makeGetConditionDescription(resModel, tree, limit, pathLimit) {
            tree = simplifyTree(tree);
            const [getFieldDef, getPathDescription] = await Promise.all([
                makeGetFieldDef(resModel, tree),
                makeGetPathDescriptions(resModel, tree, pathLimit),
            ]);
            const displayNames = await getDisplayNames(tree, getFieldDef);
            return (node) =>
                _getConditionDescription(
                    node,
                    getFieldDef,
                    getPathDescription,
                    displayNames,
                    limit,
                );
        }

        /**
         * Build a structured description of a single condition node.
         * @param {Object} node - condition tree node
         * @param {(path: string) => Object | null} getFieldDef
         * @param {(path: string) => string | undefined} getPathDescription
         * @param {Record<string, Record<number, string>>} displayNames
         * @param {number} [limit=5] - max values before truncating
         * @returns {ConditionDescription}
         */
        function _getConditionDescription(
            node,
            getFieldDef,
            getPathDescription,
            displayNames,
            limit = 5,
        ) {
            const { negate, path } = node;
            let { operator, value } = node;
            if (operator === "in range" && value[1] === "custom range") {
                operator = "between";
                value = value.slice(2);
            }
            if (["=", "!="].includes(operator) && value === false) {
                operator = operator === "=" ? "not set" : "set";
            }
            const fieldDef = getFieldDef(path);
            const operatorLabel = getOperatorLabel(
                operator,
                fieldDef?.type,
                negate,
                (operator) => {
                    switch (operator) {
                        case "=":
                        case "in":
                            return "=";
                        case "!=":
                        case "not in":
                            return _t("not =");
                        case "any":
                            return ":";
                        case "not any":
                            return _t(": not");
                    }
                },
            );

            const pathDescription = getPathDescription(path);
            const description = {
                pathDescription,
                operatorDescription: operatorLabel,
                valueDescription: null,
            };

            if (isTree(node.value)) {
                return description;
            }
            if (["set", "not set"].includes(operator)) {
                return description;
            }

            const coModeldisplayNames = displayNames[getResModel(fieldDef)];
            const dis = disambiguate(value, coModeldisplayNames);
            let values;
            if (operator === "in range") {
                const valueType = value[1];
                values = [InRange.options.find(([t]) => t === valueType)[1].toString()];
            } else {
                values = (Array.isArray(value) ? value : [value])
                    .slice(0, limit)
                    .map((val, index) =>
                        index < limit - 1
                            ? formatValue(val, dis, fieldDef, coModeldisplayNames)
                            : "...",
                    );
            }

            let join;
            let addParenthesis = Array.isArray(value);
            switch (operator) {
                case "between":
                    join = _t("and");
                    addParenthesis = false;
                    break;
                case "in range":
                    join = _t(" ");
                    addParenthesis = false;
                    break;
                case "in":
                case "not in":
                    addParenthesis = values.length === 0;
                // falls through
                default:
                    join = _t("or");
            }
            description.valueDescription = { values, join, addParenthesis };
            return description;
        }

        /**
         * Generate a human-readable string description of a domain tree.
         * Connector nodes produce "X and Y" or "X or Y"; condition nodes
         * produce "Field operator value".
         * @param {string} resModel
         * @param {import("@web/components/tree_editor/condition_tree").Tree} tree
         * @param {boolean} [isSubExpression=false] - whether to wrap in parentheses
         * @param {number} [limit] - max values per condition
         * @param {number} [pathLimit] - max path segments
         * @returns {Promise<string>}
         */
        async function getDomainTreeDescription(
            resModel,
            tree,
            isSubExpression = false,
            limit = undefined,
            pathLimit = undefined,
        ) {
            tree = simplifyTree(tree);
            if (tree.type === "connector") {
                // we assume that the domain tree is normalized (--> there is at least two children)
                const childDescriptions = tree.children.map((node) =>
                    getDomainTreeDescription(resModel, node, true),
                );
                const separator = tree.value === "&" ? _t("and") : _t("or");
                const descriptions = await Promise.all(childDescriptions);
                /** @type {string} */
                let description = descriptions.join(` ${separator} `);
                if (isSubExpression || tree.negate) {
                    description = `( ${description} )`;
                }
                if (tree.negate) {
                    description = `! ${description}`;
                }
                return description;
            }
            const getFieldDef = await makeGetFieldDef(resModel, tree);
            const getConditionDescription = await makeGetConditionDescription(
                resModel,
                tree,
                limit,
                pathLimit,
            );
            const { pathDescription, operatorDescription, valueDescription } =
                getConditionDescription(tree);
            const stringDescription = [pathDescription, operatorDescription];
            if (valueDescription) {
                const { values, join, addParenthesis } = valueDescription;
                const jointedValues = values.join(` ${join} `);
                stringDescription.push(
                    addParenthesis ? `( ${jointedValues} )` : jointedValues,
                );
            } else if (isTree(tree.value)) {
                const _fieldDef = getFieldDef(/** @type {any} */ (tree).path);
                const _resModel = getResModel(_fieldDef);
                const _tree = /** @type {any} */ (tree.value);
                const description = await getDomainTreeDescription(_resModel, _tree);
                stringDescription.push(`( ${description} )`);
            }
            return stringDescription.join(" ");
        }

        /**
         * Build indented tooltip lines for a domain tree (used in popover tooltips).
         * @param {string} resModel
         * @param {import("@web/components/tree_editor/condition_tree").Tree} tree
         * @param {number} [depth=0] - current indentation level
         * @returns {Promise<string[]>}
         */
        async function getTooltipLines(resModel, tree, depth = 0) {
            const tabs = " ".repeat(depth * 4);
            tree = simplifyTree(tree);
            if (tree.type === "connector") {
                // we assume that the domain tree is normalized (--> there is at least two children)
                let connector = tree.value === "&" ? _t("all") : _t("any");
                if (tree.negate) {
                    connector = tree.value === "&" ? _t("not all") : _t("none");
                }
                connector = `${tabs}${connector}`;
                const childrenTooltipLines = await Promise.all(
                    tree.children.map((node) =>
                        getTooltipLines(resModel, node, depth + 1),
                    ),
                );
                return [connector, ...childrenTooltipLines].flat();
            }
            const getFieldDef = await makeGetFieldDef(resModel, tree);
            const getConditionDescription = await makeGetConditionDescription(
                resModel,
                tree,
                20,
            );
            const { pathDescription, operatorDescription, valueDescription } =
                getConditionDescription(tree);
            const descr = [];
            const stringDescriptions = [pathDescription, operatorDescription];
            if (valueDescription) {
                const { values, join, addParenthesis } = valueDescription;
                const jointedValues = values.join(` ${join} `);
                stringDescriptions.push(
                    addParenthesis ? `( ${jointedValues} )` : jointedValues,
                );
            }
            descr.push(`${tabs}${stringDescriptions.join(" ")}`);
            if (isTree(tree.value)) {
                const _fieldDef = getFieldDef(/** @type {any} */ (tree).path);
                const _resModel = getResModel(_fieldDef);
                const _tree = /** @type {any} */ (tree.value);
                const tooltipLines = await getTooltipLines(_resModel, _tree, depth + 1);
                descr.push(...tooltipLines);
            }
            return descr;
        }

        /**
         * Generate a multi-line tooltip string for a domain tree.
         * @param {string} resModel
         * @param {import("@web/components/tree_editor/condition_tree").Tree} tree
         * @returns {Promise<string>}
         */
        async function getDomainTreeTooltip(resModel, tree) {
            const descriptions = await getTooltipLines(resModel, tree);
            return descriptions.join("\n");
        }

        /**
         * Build a lookup function that maps field paths to their field definitions.
         * Loads all field info for paths used in the tree in parallel.
         * @param {string} resModel
         * @param {import("@web/components/tree_editor/condition_tree").Tree} tree
         * @returns {Promise<(path: string) => Object | null>}
         */
        async function makeGetFieldDef(resModel, tree) {
            const paths = new Set(getPathsInTree(tree, true));
            const promises = [];
            const fieldDefs = {};
            for (const path of paths) {
                promises.push(
                    fieldService.loadFieldInfo(resModel, path).then(({ fieldDef }) => {
                        fieldDefs[path] = fieldDef;
                    }),
                );
            }
            await Promise.all(promises);
            return (path) => {
                if (typeof path === "string") {
                    return fieldDefs[path];
                }
                return null;
            };
        }

        /**
         * Convert a domain array into a condition tree with virtual operators.
         * @param {string} resModel
         * @param {any[]} domain - Odoo domain expression
         * @param {boolean} [distributeNot=true] - whether to push NOT down into leaves
         * @returns {Promise<import("@web/components/tree_editor/condition_tree").Tree>}
         */
        async function treeFromDomain(resModel, domain, distributeNot = true) {
            const tree = constructTreeFromDomain(domain, distributeNot);
            const getFieldDef = await makeGetFieldDef(resModel, tree);
            return introduceVirtualOperators(tree, { getFieldDef });
        }

        return {
            getDomainTreeDescription,
            getDomainTreeTooltip,
            makeGetConditionDescription,
            makeGetFieldDef,
            treeFromDomain,
        };
    },
};

registry.category("services").add("tree_processor", treeProcessorService);
