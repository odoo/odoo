import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import {
    BadgeSelectionField,
    badgeSelectionField,
} from "@web/views/fields/badge_selection/badge_selection_field";

export class BadgeSelectionWithFilterField extends BadgeSelectionField {
    static props = {
        ...BadgeSelectionField.props,
        allowedSelectionField: { type: String },
    };

    get options() {
        const allowedSelection = this.props.record.data[this.props.allowedSelectionField];
        return super.options.filter(([value, _]) => allowedSelection.includes(value));
    }
}

export const badgeSelectionFieldWithFilter = {
    ...badgeSelectionField,
    component: BadgeSelectionWithFilterField,
    displayName: _t("Badges for Selection With Filter"),
    supportedTypes: ["selection"],
    extractProps({ options }) {
        return {
            ...badgeSelectionField.extractProps(...arguments),
            allowedSelectionField: options.allowed_selection_field,
        };
    },
};

registry.category("fields").add("selection_badge_with_filter", badgeSelectionFieldWithFilter);
