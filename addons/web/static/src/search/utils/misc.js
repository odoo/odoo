import { _t } from "@web/core/l10n/translation";
import {
    connector,
    formatValue,
    isTree,
    treeFromDomain,
} from "@web/core/tree_editor/condition_tree";
import { getOperatorLabel } from "@web/core/tree_editor/tree_editor_operator_editor";
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

function groupBy(array, ...fns) {
    if (fns.length === 0) {
        return array;
    }
    const groups = new Map();
    const [fn, ...remainingFns] = fns;
    for (const element of array) {
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
        (t) => (t.type === "condition" ? formatValue(t.path) : null)
    );
}

function getShortPathDescription(pathDescription) {
    return pathDescription.split(" \u2794 ").at(-1);
}

function processValueDescription(valueDescription, operator) {
    const { values } = valueDescription;
    switch (operator) {
        case "is_not_between":
        case "between":
            return `( ${values[0]} ${_t("and")} ${values[1]} )`;
        case "last":
        case "not_last":
        case "next":
        case "not_next":
            return values.join(" ");
        default:
            return values;
    }
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
        if (["set", "not_set", "today", "not_today"].includes(tree.operator)) {
            return facet(getOperatorLabel(tree.operator).toString(), shortPathDescription);
        }
        return facet(
            processValueDescription(valueDescription, tree.operator),
            shortPathDescription
        );
    }

    if (tree.children.length === 0) {
        return facet(tree.value === "&" ? _t("True") : _t("False"));
    }
    if (tree.children.length === 1) {
        return getTreeFacet(tree.children[0], getFieldDef, getConditionDescription);
    }

    const groups = groupByTypeThenByPath(tree.children);
    if (groups.size > 1) {
        return facet(_t("Custom filter"));
    }
    if (tree.children.some((c) => c.negate) || groups.get("condition").size > 1) {
        return facet(_t("Custom filter"));
    }

    // all children are conditions on the same path without negate

    let shortPathDescription = null;
    let operator = null;
    const values = [];
    for (const child of tree.children) {
        const { pathDescription, valueDescription } = getConditionDescription(child);
        if (shortPathDescription === null) {
            shortPathDescription = getShortPathDescription(pathDescription);
        }
        if (operator === null) {
            operator = child.operator;
        }
        if (
            tree.value === "&" ||
            isTree(child.value) ||
            formatValue(child.operator) !== formatValue(operator)
        ) {
            return facet(shortPathDescription);
        }
        if (valueDescription) {
            values.push(processValueDescription(valueDescription, operator));
        }
    }

    if (["set", "not_set", "today", "not_today"].includes(operator)) {
        return facet(getOperatorLabel(operator).toString(), shortPathDescription);
    }

    return facet(values, shortPathDescription);
}

function isAndConnector(tree) {
    return tree.type === "connector" && !tree.negate && tree.value === "&";
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
