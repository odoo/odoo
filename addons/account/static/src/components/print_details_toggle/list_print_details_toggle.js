import { registry } from "@web/core/registry";
import { listBooleanToggleField, ListBooleanToggleField } from "@web/views/fields/boolean_toggle/list_boolean_toggle_field";

export class ListPrintDetailsToggleField extends ListBooleanToggleField {
    static template = "account.ListPrintDetailsToggleField";
}

export const listPrintDetailsToggleField = {
    ...listBooleanToggleField,
    component: ListPrintDetailsToggleField,
};

registry.category("fields").add("list.print_details_boolean_toggle", listPrintDetailsToggleField);
