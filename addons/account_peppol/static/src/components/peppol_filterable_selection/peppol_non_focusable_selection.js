import { registry } from "@web/core/registry";
import { SelectMenu } from "@web/components/select_menu/select_menu";
import { SelectionField, selectionField } from "@web/fields/selection/selection/selection_field";

class NonFocusableSelectMenu extends SelectMenu {
    static template = "account_peppol.NonFocusableSelectMenu";
}

class NonFocusableSelectionField extends SelectionField {
    static components = {
        ...SelectionField.components,
        SelectMenu: NonFocusableSelectMenu,
    };
}

export const nonFocusableSelectionField = {
    ...selectionField,
    component: NonFocusableSelectionField,
};

registry.category("fields").add("peppol_non_focusable_selection", nonFocusableSelectionField);
