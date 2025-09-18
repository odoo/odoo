// @ts-check

/** @module @web/fields/selection/badge_selection/badge_selection_field - Clickable badge group field for Selection and Many2one columns */

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { SelectionLikeField } from "@web/fields/selection/selection_like_field";
import { standardFieldProps } from "@web/fields/standard_field_props";

export class BadgeSelectionField extends SelectionLikeField {
    static template = "web.BadgeSelectionField";
    static props = {
        ...standardFieldProps,
        domain: { type: [Array, Function], optional: true },
        size: {
            type: String,
            optional: true,
            validate: (s) => ["sm", "md", "lg"].includes(s),
            default: "md",
        },
    };

    get options() {
        switch (this.type) {
            case "many2one":
                return this.specialData.data;
            case "selection":
                return this.props.record.fields[this.props.name].selection;
            default:
                return [];
        }
    }

    /**
     * @param {string | number | false} value
     */
    onChange(value) {
        switch (this.type) {
            case "many2one":
                if (value === false) {
                    this.props.record.update({ [this.props.name]: false });
                } else {
                    const option = this.options.find((option) => option[0] === value);
                    this.props.record.update({
                        [this.props.name]: {
                            id: option[0],
                            display_name: option[1],
                        },
                    });
                }
                break;
            case "selection":
                if (value === this.value) {
                    const { required } = this.props.record.fields[this.props.name];
                    if (!required) {
                        this.props.record.update({ [this.props.name]: false });
                    }
                } else {
                    this.props.record.update({ [this.props.name]: value });
                }
                break;
        }
    }
}

export const badgeSelectionField = {
    component: BadgeSelectionField,
    displayName: _t("Badges"),
    supportedTypes: ["many2one", "selection"],
    supportedOptions: [
        {
            label: "Size",
            name: "size",
            type: "selection",
            choices: [
                { label: "Small", value: "sm" },
                { label: "Medium", value: "md" },
                { label: "Large", value: "lg" },
            ],
            default: "md",
        },
    ],
    isEmpty: (record, fieldName) => record.data[fieldName] === false,
    extractProps: (fieldInfo, dynamicInfo) => ({
        domain: dynamicInfo.domain,
        size: fieldInfo.options.size,
    }),
};

registry.category("fields").add("selection_badge", badgeSelectionField);
