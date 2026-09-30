import { registry } from "@web/core/registry";
import { SelectMenu } from "@web/core/select_menu/select_menu";
import { SelectionField, selectionField } from "@web/views/fields/selection/selection_field";

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
