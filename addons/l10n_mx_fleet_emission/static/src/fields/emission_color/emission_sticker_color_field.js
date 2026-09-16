/** @odoo-module native */
import { _t } from "@web/core/translation";
import { registerField } from "@web/fields/_registry";
import { SelectionLikeField } from "@web/fields/selection/selection_like_field";
import { standardFieldProps } from "@web/fields/standard_field_props";

export class EmissionStickerColorField extends SelectionLikeField {
    static template = "l10n_mx_fleet_emission.EmissionStickerColorField";
    static props = {
        ...standardFieldProps,
        size: {
            type: String,
            optional: true,
            validate: (s) => ["sm", "md", "lg"].includes(s),
        },
        periodField: { type: String, optional: true },
    };
    static defaultProps = { size: "md" };

    get colorClass() {
        return this.value ? `o_l10n_mx_emission_sticker_${this.value}` : "";
    }

    get period() {
        const { periodField, record } = this.props;
        return periodField ? record.data[periodField] || "" : "";
    }
}

export const emissionStickerColorField = {
    component: EmissionStickerColorField,
    displayName: _t("Emissions Sticker Color"),
    supportedTypes: ["selection"],
    supportedOptions: [
        {
            label: _t("Size"),
            name: "size",
            type: "selection",
            choices: [
                { label: _t("Small"), value: "sm" },
                { label: _t("Medium"), value: "md" },
                { label: _t("Large"), value: "lg" },
            ],
        },
        {
            label: _t("Period field"),
            name: "period_field",
            type: "string",
            help: _t(
                "Char field holding the inspection window, shown beside the color.",
            ),
        },
    ],
    extractProps: ({ options }) => ({
        size: options.size,
        periodField: options.period_field,
    }),
};

registerField("emission_sticker_color", emissionStickerColorField);
