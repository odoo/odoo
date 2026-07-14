import { registry } from "@web/core/registry";
import { SelectionField, selectionField } from "@web/views/fields/selection/selection_field";

class NonFocusableSelectionField extends SelectionField {
    static template = "account_peppol.NonFocusableSelectionField";
}

export const nonFocusableSelectionField = {
    ...selectionField,
    component: NonFocusableSelectionField,
};

registry.category("fields").add("peppol_non_focusable_selection", nonFocusableSelectionField);
