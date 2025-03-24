import { getDomainDisplayedOperators } from "@web/core/domain_selector/domain_selector_operator_editor";
import { loadFields } from "@web/core/field_service";
import { condition, domainFromTree } from "@web/core/tree_editor/condition_tree";
import { getDefaultValue } from "@web/core/tree_editor/tree_editor_value_editors";
import { getDefaultPath } from "@web/core/tree_editor/utils";

export function getDefaultCondition(fieldDefs) {
    const defaultPath = getDefaultPath(fieldDefs);
    const fieldDef = fieldDefs[defaultPath];
    const operator = getDomainDisplayedOperators(fieldDef)[0];
    const value = getDefaultValue(fieldDef, operator);
    return condition(fieldDef.name, operator, value);
}

export function getDefaultDomain(fieldDefs) {
    return domainFromTree(getDefaultCondition(fieldDefs));
}

export function useGetDefaultLeafDomain() {
    return async (resModel) => {
        const fieldDefs = await loadFields(resModel);
        return getDefaultDomain(fieldDefs);
    };
}
