import {
    deserializeDate,
    deserializeDateTime,
    formatDate,
    formatDateTime,
} from "@web/core/l10n/dates";
import { parseTime } from "@web/core/l10n/time";
import { _t } from "@web/core/l10n/translation";
import { useLoadFieldInfo, useLoadPathDescription } from "@web/core/model_field_selector/utils";
import {
    condition,
    Expression,
    isTree,
    normalizeValue,
    splitPath,
} from "@web/core/tree_editor/condition_tree";
import { OPTIONS_WITH_SELECT } from "@web/core/tree_editor/tree_editor_datetime_options";
import { getOperatorLabel } from "@web/core/tree_editor/tree_editor_operator_editor";
import { unique, zip } from "@web/core/utils/arrays";
import { useService } from "@web/core/utils/hooks";
import { Within } from "./tree_editor_components";

/**
 * @param {import("@web/core/tree_editor/condition_tree").Value} val
 * @param {boolean} disambiguate
 * @param {Object|null} fieldDef
 * @param {Object} displayNames
 * @returns
 */
function formatValue(val, disambiguate, fieldDef, displayNames) {
    if (
        fieldDef?.type === "date_option" &&
        fieldDef.name in OPTIONS_WITH_SELECT &&
        typeof val !== "string"
    ) {
        const options = OPTIONS_WITH_SELECT[fieldDef.name];
        const valToCompare = val instanceof Expression ? val._expr : val;
        const [, label] = (options || []).find(([v]) => v === valToCompare) || [];
        if (label !== undefined) {
            val = label;
        }
    }
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
        if (
            fieldDef?.type === "date" ||
            (fieldDef?.type === "datetime_option" && fieldDef.name === "__date")
        ) {
            return formatDate(deserializeDate(val));
        }
        if (fieldDef?.type === "datetime_option" && fieldDef.name === "__time") {
            return parseTime(val, true).toString(true);
        }
    }
    if (disambiguate && typeof val === "string") {
        return JSON.stringify(val);
    }
    return val;
}

export function isId(value) {
    return Number.isInteger(value) && value >= 1;
}

export function disambiguate(value, displayNames) {
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

export function useMakeGetFieldDef(fieldService) {
    fieldService ||= useService("field");
    const loadFieldInfo = useLoadFieldInfo(fieldService);
    return async (resModel, tree, additionalsPath = []) => {
        const pathsInTree = getPathsInTree(tree, true);
        const paths = new Set([...pathsInTree, ...additionalsPath]);
        const promises = [];
        const fieldDefs = {};
        for (const path of paths) {
            promises.push(
                loadFieldInfo(resModel, path).then(({ fieldDef }) => {
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
    };
}

function useGetTreePathDescription(fieldService) {
    fieldService ||= useService("field");
    const loadPathDescription = useLoadPathDescription(fieldService);
    return async (resModel, tree) => {
        const paths = getPathsInTree(tree);
        const promises = [];
        const pathDescriptions = new Map();
        for (const path of paths) {
            promises.push(
                loadPathDescription(resModel, path).then(({ displayNames }) => {
                    pathDescriptions.set(path, displayNames.join(" \u2794 "));
                })
            );
        }
        await Promise.all(promises);
        return (path) => pathDescriptions.get(path);
    };
}

async function getDisplayNames(tree, getFieldDef, nameService) {
    const resIdsByModel = extractIdsFromTree(tree, getFieldDef);
    const proms = [];
    const resModels = [];
    for (const [resModel, resIds] of Object.entries(resIdsByModel)) {
        resModels.push(resModel);
        proms.push(nameService.loadDisplayNames(resModel, resIds));
    }
    return Object.fromEntries(zip(resModels, await Promise.all(proms)));
}

export function useMakeGetConditionDescription(fieldService, nameService) {
    const makeGetPathDescriptions = useGetTreePathDescription(fieldService);
    return async (resModel, tree, getFieldDef) => {
        tree = simplifyTree(tree);
        const [displayNames, getPathDescription] = await Promise.all([
            getDisplayNames(tree, getFieldDef, nameService),
            makeGetPathDescriptions(resModel, tree),
        ]);
        return (node) =>
            _getConditionDescription(node, getFieldDef, getPathDescription, displayNames);
    };
}

function _getConditionDescription(node, getFieldDef, getPathDescription, displayNames) {
    let { operator, negate, value, path } = node;
    if (["=", "!="].includes(operator) && value === false) {
        operator = operator === "=" ? "not_set" : "set";
    } else if (["in", "not in"].includes(operator) && Array.isArray(value) && value.length === 0) {
        operator = operator === "in" ? "not_set" : "set";
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
    if (["set", "not_set", "today", "not_today"].includes(operator)) {
        return description;
    }

    const coModeldisplayNames = displayNames[getResModel(fieldDef)];
    const dis = disambiguate(value, coModeldisplayNames);
    const values = ["next", "not_next", "last", "not_last"].includes(operator)
        ? [value[0], Within.options.find((option) => option[0] === value[1])[1]]
        : (Array.isArray(value) ? value : [value])
              .slice(0, 5)
              .map((val, index) =>
                  index < 4 ? formatValue(val, dis, fieldDef, coModeldisplayNames) : "..."
              );
    let join;
    let addParenthesis = Array.isArray(value);
    switch (operator) {
        case "is_not_between":
        case "between":
            join = _t("and");
            addParenthesis = false;
            break;
        case "last":
        case "not_last":
        case "next":
        case "not_next":
            join = " ";
            addParenthesis = false;
            break;
        case "in":
        case "not in":
            addParenthesis = false;
        // eslint-disable-next-line no-fallthrough
        default:
            join = _t("or");
    }
    description.valueDescription = { values, join, addParenthesis };
    return description;
}

export function useGetTreeDescription(fieldService, nameService) {
    fieldService ||= useService("field");
    nameService ||= useService("name");
    const makeGetFieldDef = useMakeGetFieldDef(fieldService);
    const makeGetConditionDescription = useMakeGetConditionDescription(fieldService, nameService);
    return async (resModel, tree) => {
        async function getTreeDescription(resModel, tree, isSubExpression = false) {
            tree = simplifyTree(tree);
            if (tree.type === "connector") {
                // we assume that the domain tree is normalized (--> there is at least two children)
                const childDescriptions = tree.children.map((node) =>
                    getTreeDescription(resModel, node, true)
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
                getFieldDef
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
                const description = await getTreeDescription(_resModel, _tree);
                stringDescription.push(`( ${description} )`);
            }
            return stringDescription.join(" ");
        }
        return getTreeDescription(resModel, tree);
    };
}

export function useGetTreeTooltip(fieldService, nameService) {
    fieldService ||= useService("field");
    nameService ||= useService("name");
    const makeGetFieldDef = useMakeGetFieldDef(fieldService);
    const makeGetConditionDescription = useMakeGetConditionDescription(fieldService, nameService);
    return async (resModel, tree) => {
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
            const getConditionDescription = await makeGetConditionDescription(
                resModel,
                tree,
                getFieldDef
            );
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
        const descriptions = await getTooltipLines(resModel, tree);
        return descriptions.join("\n");
    };
}

export function getResModel(fieldDef) {
    if (fieldDef) {
        return fieldDef.is_property ? fieldDef.comodel : fieldDef.relation;
    }
    return null;
}

function extractIdsFromTree(tree, getFieldDef) {
    const idsByModel = _extractIdsRecursive(tree, getFieldDef, {});

    for (const resModel in idsByModel) {
        idsByModel[resModel] = unique(idsByModel[resModel]);
    }

    return idsByModel;
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

function makePaths(path) {
    const paths = [path];
    const { initialPath, lastPart } = splitPath(path);
    if (initialPath && lastPart) {
        // these paths are used in _createSpecialPaths
        paths.push(
            initialPath,
            [initialPath, "__date"].join("."),
            [initialPath, "__time"].join("."),
            [initialPath, "__date", lastPart].join("."),
            [initialPath, "__time", lastPart].join(".")
        );
    }
    return paths;
}

function _getPathsInTree(tree, lookInSubTrees = false) {
    const paths = [];
    if (tree.type === "condition") {
        paths.push(tree.path);
        if (typeof tree.path === "string" && lookInSubTrees && isTree(tree.value)) {
            const subTreePaths = _getPathsInTree(tree.value, lookInSubTrees);
            for (const p of subTreePaths) {
                if (typeof p === "string") {
                    paths.push(`${tree.path}.${p}`);
                }
            }
        }
    }
    if (tree.type === "connector" && tree.children) {
        for (const child of tree.children) {
            paths.push(..._getPathsInTree(child, lookInSubTrees));
        }
    }
    return unique(paths);
}

function getPathsInTree(tree, lookInSubTrees = false) {
    const paths = _getPathsInTree(tree, lookInSubTrees);
    return paths.flatMap((p) => makePaths(p));
}

const SPECIAL_FIELDS = ["country_id", "user_id", "partner_id", "stage_id", "id"];

export function getDefaultPath(fieldDefs) {
    for (const name of SPECIAL_FIELDS) {
        const fieldDef = fieldDefs[name];
        if (fieldDef) {
            return fieldDef.name;
        }
    }
    const name = Object.keys(fieldDefs)[0];
    if (name) {
        return name;
    }
    throw new Error(`No field found`);
}

/**
 * @param {Tree} tree
 * @returns {tree}
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
        children[childrenByPath[path].index] = condition(path, "in", normalizeValue(unique(value)));
    }
    if (children.length === 1) {
        return { ...children[0] };
    }
    return { ...tree, children };
}
