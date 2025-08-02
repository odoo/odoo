import { registry } from "@web/core/registry";
import { FilterableSelectionField, filterableSelectionField } from "@web/views/fields/selection/filterable_selection_field";

// for falsy option, display placeholder in the select options instead of an empty field
export class AccountSendingMethodSelection extends FilterableSelectionField {
    static template = "account.AccountSendingMethodSelection";
}

export const accountSendingMethodSelection = {
    ...filterableSelectionField,
    component: AccountSendingMethodSelection,
};

registry.category("fields").add("account_sending_method_selection", accountSendingMethodSelection);
