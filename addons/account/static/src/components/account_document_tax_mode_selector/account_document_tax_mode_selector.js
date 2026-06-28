import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { BadgesSelectionField } from "@web/views/fields/badges_selection/badges_selection_field";

export const accountDocumentTaxModeSelector = {
    component: BadgesSelectionField,
    displayName: _t("Badges"),
    supportedTypes: ["selection"],
    extractProps: ({ options }, dynamicInfo) => ({
        canDeselect: false,
    }),
};

registry.category("fields").add("document_tax_mode_selector", accountDocumentTaxModeSelector);
