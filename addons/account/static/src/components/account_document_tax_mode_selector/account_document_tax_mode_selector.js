import { registry } from "@web/core/registry";
import { BadgesSelectionField } from "@web/views/fields/badges_selection/badges_selection_field";
import { BaseBadgesField } from "@web/views/fields/badges_selection/base_badges_field";


export class AccountBadgesSelectionFieldBase extends BaseBadgesField{
    static template = "account.DocumentTaxModeSelector";
};

export class AccountDocumentTaxModeSelector extends BadgesSelectionField{
    static components = {
        ...BadgesSelectionField.components,
        BaseBadgesField: AccountBadgesSelectionFieldBase,
    };
}

export const accountDocumentTaxModeSelector = {
    component: AccountDocumentTaxModeSelector,
}

registry.category("fields").add("document_tax_mode_selector", accountDocumentTaxModeSelector);
