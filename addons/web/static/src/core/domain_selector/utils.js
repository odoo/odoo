import { getDomainDisplayedOperators } from "@web/core/domain_selector/domain_selector_operator_editor";
import { Condition } from "@web/core/tree_editor/condition_tree";
import { getDefaultValue } from "@web/core/tree_editor/tree_editor_value_editors";
import { getDefaultPath } from "@web/core/tree_editor/utils";
import { useService } from "@web/core/utils/hooks";

export function getDefaultCondition(fieldDefs) {
    const defaultPath = getDefaultPath(fieldDefs);
    const fieldDef = fieldDefs[defaultPath];
    const operator = getDomainDisplayedOperators(fieldDef)[0];
    const value = getDefaultValue(fieldDef, operator);
    return Condition.of(fieldDef.name, operator, value);
}

export function getDefaultDomain(fieldDefs) {
    return getDefaultCondition(fieldDefs).toDomainRepr();
}

export function useGetDefaultLeafDomain() {
    const fieldService = useService("field");
    return async (resModel) => {
        const fieldDefs = await fieldService.loadFields(resModel);
        return getDefaultDomain(fieldDefs);
    };
}
