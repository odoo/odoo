import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import {
    BadgeSelectionField,
    badgeSelectionField,
} from "@web/views/fields/badge_selection/badge_selection_field";

export class BadgeSelectionWithFilterField extends BadgeSelectionField {
    static props = {
        ...BadgeSelectionField.props,
        allowed_selection: { type: Array },
    };

    get options() {
        return super.options.filter(([value, _]) => this.props.allowed_selection.includes(value));
    }
}

export const badgeSelectionFieldWithFilter = {
    ...badgeSelectionField,
    component: BadgeSelectionWithFilterField,
    displayName: _t("Badges for Selection With Filter"),
    supportedTypes: ["selection"],
    extractProps({ options }, { context: { allowed_selection } }) {
        return {
            ...badgeSelectionField.extractProps(...arguments),
            allowed_selection: allowed_selection,
        };
    },
};

registry.category("fields").add("selection_badge_with_filter", badgeSelectionFieldWithFilter);
