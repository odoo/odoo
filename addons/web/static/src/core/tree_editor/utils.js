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
    Couple,
    createVirtualOperators,
    Expression,
    isTree,
    normalizeValue,
    splitPath,
} from "@web/core/tree_editor/condition_tree";
import { OPTIONS } from "@web/core/tree_editor/tree_editor_datetime_options";
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
    if (fieldDef?.type === "date_option" && fieldDef.name in OPTIONS && typeof val !== "string") {
        const options = OPTIONS[fieldDef.name];
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
        const loadFieldInfoFromMultiplePaths = async (resModel, fieldDefs, path) => {
            if (typeof path === "string" && !(path in fieldDefs)) {
                const prom = loadFieldInfo(resModel, path).then(({ fieldDef }) => {
                    fieldDefs[path].fieldDef = fieldDef;
                    return fieldDef?.relation || null;
                });
                fieldDefs[path] = { prom, pathFieldDefs: {}, fieldDef: null };
                return prom;
            }
            if (path instanceof Couple && typeof path.fst === "string" && path.fst in fieldDefs) {
                const resModel = await fieldDefs[path.fst].prom;
                if (resModel) {
                    return loadFieldInfoFromMultiplePaths(
                        resModel,
                        fieldDefs[path.fst].pathFieldDefs,
                        path.snd
                    );
                }
            }
            return null;
        };
        for (const path of paths) {
            promises.push(loadFieldInfoFromMultiplePaths(resModel, fieldDefs, path));
        }
        await Promise.all(promises);
        const _getFieldDef = (path, fieldDefs) => {
            if (typeof path === "string") {
                return fieldDefs[path].fieldDef;
            }
            if (path instanceof Couple && typeof path.fst === "string" && path.fst in fieldDefs) {
                return _getFieldDef(path.snd, fieldDefs[path.fst].pathFieldDefs);
            }
            return null;
        };
        return (path) => _getFieldDef(path, fieldDefs);
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
    const nodeWithVirtualOperators = createVirtualOperators(node, { getFieldDef });
    const { operator, negate, value, path } = nodeWithVirtualOperators;
    const fieldDef = getFieldDef(path);
    const operatorLabel = getOperatorLabel(operator, fieldDef?.type, negate);
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
            join = ",";
            break;
        default:
            join = _t("or");
    }
    description.valueDescription = { values, join, addParenthesis };
    return description;
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

function addPaths(paths, path) {
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
}

export function getPathsInTree(tree, lookInSubTrees = false) {
    const paths = [];
    if (tree.type === "condition") {
        paths.push(tree.path);
        if (typeof tree.path === "string") {
            addPaths(paths, tree.path);
        }
        if (lookInSubTrees && isTree(tree.value)) {
            const subTreePaths = getPathsInTree(tree.value, lookInSubTrees);
            for (const p of subTreePaths) {
                paths.push(new Couple(tree.path, p));
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
export function simplifyTree(tree) {
    if (tree.type === "condition") {
        return tree;
    }
    const processedChildren = tree.children.map(simplifyTree);
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
        children.push(condition(path, "in", normalizeValue(unique(value))));
    }
    if (children.length === 1) {
        return { ...children[0] };
    }
    return { ...tree, children };
}
