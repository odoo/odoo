import {
    deserializeDate,
    deserializeDateTime,
    formatDate,
    formatDateTime,
} from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { getOperatorLabel } from "@web/core/tree_editor/tree_editor_operator_editor";
import { unique, zip } from "@web/core/utils/arrays";
import { condition, Expression, isTree, normalizeValue } from "./condition_tree";
import { constructTreeFromDomain } from "./construct_tree_from_domain";
import { disambiguate, getResModel, isId } from "./utils";
import { introduceVirtualOperators } from "./virtual_operators";
import { InRange } from "./tree_editor_components";

/**
 * @param {import("@web/core/tree_editor/condition_tree").Value} val
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
        children[childrenByPath[path].index] = condition(path, "in", normalizeValue(unique(value)));
    }
    if (children.length === 1) {
        return { ...children[0] };
    }
    return { ...tree, children };
}

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

function extractIdsFromTree(tree, getFieldDef) {
    const idsByModel = _extractIdsRecursive(tree, getFieldDef, {});

    for (const resModel in idsByModel) {
        idsByModel[resModel] = unique(idsByModel[resModel]);
    }

    return idsByModel;
}

export const treeProcessorService = {
    dependencies: ["field", "name"],
    async: [
        "getDomainTreeDescription",
        "getDomainTreeTooltip",
        "makeGetConditionDescription",
        "makeGetFieldDef",
        "treeFromDomain",
    ],
    start(_, { field: fieldService, name: nameService }) {
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

        async function makeGetPathDescriptions(resModel, tree, limit) {
            const paths = getPathsInTree(tree);
            const promises = [];
            const pathDescriptions = new Map();
            for (const path of paths) {
                promises.push(
                    fieldService.loadPathDescription(resModel, path).then(({ displayNames }) => {
                        pathDescriptions.set(
                            path,
                            `${displayNames.slice(0, limit).join(" \u2794 ")}${
                                displayNames.length > limit ? "..." : ""
                            }`
                        );
                    })
                );
            }
            await Promise.all(promises);
            return (path) => pathDescriptions.get(path);
        }

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
                    limit
                );
        }

        function _getConditionDescription(
            node,
            getFieldDef,
            getPathDescription,
            displayNames,
            limit = 5
        ) {
            let { operator, negate, value, path } = node;
            if (operator === "in range" && value[1] === "custom range") {
                operator = "between";
                value = value.slice(2);
            }
            if (["=", "!="].includes(operator) && value === false) {
                operator = operator === "=" ? "not set" : "set";
            }
            const fieldDef = getFieldDef(path);
            const operatorLabel = getOperatorLabel(operator, fieldDef?.type, negate, (operator) => {
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
            });

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
                            : "..."
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
                // eslint-disable-next-line no-fallthrough
                default:
                    join = _t("or");
            }
            description.valueDescription = { values, join, addParenthesis };
            return description;
        }

        async function getDomainTreeDescription(
            resModel,
            tree,
            isSubExpression = false,
            limit = undefined,
            pathLimit = undefined
        ) {
            tree = simplifyTree(tree);
            if (tree.type === "connector") {
                // we assume that the domain tree is normalized (--> there is at least two children)
                const childDescriptions = tree.children.map((node) =>
                    getDomainTreeDescription(resModel, node, true)
                );
                const separator = tree.value === "&" ? _t("and") : _t("or");
                let description = await Promise.all(childDescriptions);
                description = description.join(` ${separator} `);
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
                pathLimit
            );
            const { pathDescription, operatorDescription, valueDescription } =
                getConditionDescription(tree);
            const stringDescription = [pathDescription, operatorDescription];
            if (valueDescription) {
                const { values, join, addParenthesis } = valueDescription;
                const jointedValues = values.join(` ${join} `);
                stringDescription.push(addParenthesis ? `( ${jointedValues} )` : jointedValues);
            } else if (isTree(tree.value)) {
                const _fieldDef = getFieldDef(tree.path);
                const _resModel = getResModel(_fieldDef);
                const _tree = tree.value;
                const description = await getDomainTreeDescription(_resModel, _tree);
                stringDescription.push(`( ${description} )`);
            }
            return stringDescription.join(" ");
        }

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
                    tree.children.map((node) => getTooltipLines(resModel, node, depth + 1))
                );
                return [connector, ...childrenTooltipLines].flat();
            }
            const getFieldDef = await makeGetFieldDef(resModel, tree);
            const getConditionDescription = await makeGetConditionDescription(resModel, tree, 20);
            const { pathDescription, operatorDescription, valueDescription } =
                getConditionDescription(tree);
            const descr = [];
            const stringDescriptions = [pathDescription, operatorDescription];
            if (valueDescription) {
                const { values, join, addParenthesis } = valueDescription;
                const jointedValues = values.join(` ${join} `);
                stringDescriptions.push(addParenthesis ? `( ${jointedValues} )` : jointedValues);
            }
            descr.push(`${tabs}${stringDescriptions.join(" ")}`);
            if (isTree(tree.value)) {
                const _fieldDef = getFieldDef(tree.path);
                const _resModel = getResModel(_fieldDef);
                const _tree = tree.value;
                const tooltipLines = await getTooltipLines(_resModel, _tree, depth + 1);
                descr.push(...tooltipLines);
            }
            return descr;
        }

        async function getDomainTreeTooltip(resModel, tree) {
            const descriptions = await getTooltipLines(resModel, tree);
            return descriptions.join("\n");
        }

        async function makeGetFieldDef(resModel, tree) {
            const paths = new Set(getPathsInTree(tree, true));
            const promises = [];
            const fieldDefs = {};
            for (const path of paths) {
                promises.push(
                    fieldService.loadFieldInfo(resModel, path).then(({ fieldDef }) => {
                        fieldDefs[path] = fieldDef;
                    })
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
