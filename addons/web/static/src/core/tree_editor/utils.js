/** @odoo-module **/

import { unique, zip } from "@web/core/utils/arrays";
import { getOperatorLabel } from "@web/core/tree_editor/tree_editor_operator_editor";
import { Expression } from "@web/core/tree_editor/condition_tree";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { deserializeDate, deserializeDateTime, formatDate, formatDateTime } from "../l10n/dates";

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

export function leafToString(tree, fieldDef, displayNames) {
    const { operator, negate, value } = tree;
    const operatorLabel = getOperatorLabel(operator, negate);

    const description = {
        operatorDescription: `${operatorLabel}`,
        valueDescription: null,
    };

    if (["set", "not_set"].includes(operator)) {
        return description;
    }
    if (["is", "is_not"].includes(operator)) {
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
    switch (operator) {
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

export function getResModel(fieldDef) {
    if (fieldDef) {
        return fieldDef.is_property ? fieldDef.comodel : fieldDef.relation;
    }
    return null;
}

export function extractIdsFromTree(tree, getFieldDef) {
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
            const ids = values.filter((val) => Number.isInteger(val) && val >= 1);
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

export function getPathsInTree(tree) {
    const paths = [];
    if (tree.type === "condition") {
        paths.push(tree.path);
    }
    if (tree.type === "connector" && tree.children) {
        for (const child of tree.children) {
            paths.push(...getPathsInTree(child));
        }
    }
    return paths;
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
