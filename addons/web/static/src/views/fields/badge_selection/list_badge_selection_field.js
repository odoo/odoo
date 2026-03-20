import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { mergeClasses } from "@web/core/utils/classname";
import { badgeSelectionField, BadgeSelectionField } from "./badge_selection_field";

export class ListBadgeSelectionField extends BadgeSelectionField {
    static template = "web.ListBadgeSelectionField";
    static props = {
        ...BadgeSelectionField.props,
        colorField: { type: String, optional: true },
    };
    getBadgeClassNames(option = false) {
        if (this.props.readonly) {
            if (
                this.props.colorField &&
                Number.isInteger(this.props.record.data[this.props.colorField])
            ) {
                return `o_badge_color_${this.props.record.data[this.props.colorField]}`;
            }
            return mergeClasses({ "btn btn-secondary": this.value });
        }
        return mergeClasses({
            "active o_badge_border": this.value === option[0],
            "btn-sm": this.props.size === "sm",
            "btn-lg": this.props.size === "lg",
        });
    }
}

export const listBadgeSelectionField = {
    ...badgeSelectionField,
    component: ListBadgeSelectionField,
    supportedOptions: [
        ...badgeSelectionField.supportedOptions,
        {
            label: _t("Color field"),
            name: "color_field",
            type: "field",
            availableTypes: ["integer"],
            help: _t("Set an integer field to use colors with the badge."),
        },
    ],
    extractProps: (fieldInfo, dynamicInfo) => ({
        ...badgeSelectionField.extractProps(fieldInfo, dynamicInfo),
        colorField: fieldInfo.options.color_field,
    }),
};

registry.category("fields").add("list.selection_badge", listBadgeSelectionField);
