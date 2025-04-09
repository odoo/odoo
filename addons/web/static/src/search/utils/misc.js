import { _t } from "@web/core/l10n/translation";
import {
    connector,
    formatValue,
    isTree,
    treeFromDomain,
} from "@web/core/tree_editor/condition_tree";
import {
    simplifyTree,
    useMakeGetConditionDescription,
    useMakeGetFieldDef,
} from "@web/core/tree_editor/utils";
import { ensureArray } from "@web/core/utils/arrays";
import { useService } from "@web/core/utils/hooks";

export const FACET_ICONS = {
    filter: "fa fa-filter",
    groupBy: "oi oi-group",
    groupByAsc: "fa fa-sort-numeric-asc",
    groupByDesc: "fa fa-sort-numeric-desc",
    favorite: "fa fa-star",
};

export const FACET_COLORS = {
    filter: "primary",
    groupBy: "action",
    favorite: "warning",
};

export const GROUPABLE_TYPES = [
    "boolean",
    "char",
    "date",
    "datetime",
    "integer",
    "many2one",
    "many2many",
    "selection",
    "tags",
];

export function facet(values, title) {
    values = ensureArray(values);
    if (typeof title === "string") {
        return { type: "field", title, values, separator: _t("or") };
    }
    return {
        type: "filter",
        values,
        separator: _t("or"),
        icon: FACET_ICONS.filter,
        color: FACET_COLORS.filter,
    };
}

function getShortPathDescription(pathDescription) {
    return pathDescription.split(" \u2794 ").at(-1);
}

function getTreeFacet(tree, getFieldDef, getConditionDescription) {
    if (tree.negate) {
        return facet(_t("Custom filter"));
    }
    if (tree.type === "condition") {
        const { pathDescription, valueDescription } = getConditionDescription(tree);
        const shortPathDescription = getShortPathDescription(pathDescription);
        if (isTree(tree.value)) {
            return facet(shortPathDescription);
        }
        if (["set", "not_set"].includes(tree.operator)) {
            return facet(tree.operator === "set" ? _t("set") : _t("not set"), shortPathDescription);
        }
        return facet(valueDescription.values, shortPathDescription);
    }
    const groups = groupByTypeThenByPath(tree.children);
    if (groups.size === 0) {
        return facet(tree.value === "&" ? _t("True") : _t("False"));
    }
    if (groups.size === 1) {
        return getTreeFacet(tree.children[0], getFieldDef, getConditionDescription);
    }
    if (tree.children.some((c) => c.type === "connector" || c.negate)) {
        return facet(_t("Custom filter"));
    }
    let someChildHasATreeValue = false;
    let pathExpr = null;
    let shortPathDescription;
    const operators = {};
    const valueDescriptions = [];
    for (const child of tree.children) {
        const { pathDescription, valueDescription } = getConditionDescription(child);
        const childPathExpr = formatValue(child.path);
        if (pathExpr === null) {
            pathExpr = childPathExpr;
            shortPathDescription = getShortPathDescription(pathDescription);
        } else if (childPathExpr !== pathExpr) {
            return facet(_t("Custom filter"));
        }

        if (isTree(child.value)) {
            someChildHasATreeValue = true;
        }
        operators[formatValue(child.operator)] = child.operator;
        valueDescriptions.push(valueDescription);
    }
    if (tree.value === "|" && Object.values(operators).length === 1 && !someChildHasATreeValue) {
        const values = [];
        const operator = Object.values(operators)[0];
        for (const valueDescription of valueDescriptions) {
            if (["set", "not_set"].includes(operator)) {
                return facet(operator === "set" ? _t("set") : _t("not set"), shortPathDescription);
            }
            values.push(...valueDescription.values);
        }
        return facet(values, shortPathDescription);
    }
    return facet(shortPathDescription);
}

function isAndConnector(tree) {
    return tree.type === "connector" && !tree.negate && tree.value === "&";
}

export function groupBy(iterable, ...fns) {
    if (fns.length === 0) {
        return iterable;
    }
    const groups = new Map();
    const [fn, ...remainingFns] = fns;
    for (const element of iterable) {
        const v = fn(element);
        if (!groups.has(v)) {
            groups.set(v, []);
        }
        groups.get(v).push(element);
    }
    const result = new Map();
    for (const [v, g] of groups) {
        result.set(v, groupBy(g, ...remainingFns));
    }
    return result;
}

function groupByTypeThenByPath(trees) {
    return groupBy(
        trees,
        (t) => t.type,
        (t) => t.type === "condition" && formatValue(t.path)
    );
}

export function useGetDomainFacets(fieldService, nameService) {
    fieldService ||= useService("field");
    nameService ||= useService("name");
    const makeGetFieldDef = useMakeGetFieldDef(fieldService);
    const makeGetConditionDescription = useMakeGetConditionDescription(fieldService, nameService);
    return async (resModel, domain, options = {}) => {
        const getFieldDef = await makeGetFieldDef(resModel, treeFromDomain(domain));
        const tree = simplifyTree(treeFromDomain(domain, { distributeNot: true, getFieldDef }));
        const getConditionDescription = await makeGetConditionDescription(
            resModel,
            tree,
            getFieldDef
        );
        const trees = [];
        if (options.splitAndConnector && isAndConnector(tree)) {
            const groups = groupByTypeThenByPath(tree.children);
            for (const [type, group] of groups) {
                for (const [, subGroup] of group) {
                    if (type === "connector") {
                        trees.push(...subGroup);
                    } else {
                        trees.push(connector("&", subGroup));
                    }
                }
            }
        } else {
            trees.push(tree);
        }
        return trees.map((tree) => getTreeFacet(tree, getFieldDef, getConditionDescription));
    };
}
