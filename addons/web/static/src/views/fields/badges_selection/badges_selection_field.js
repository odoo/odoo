import { BaseBadgeField, extractStandardFieldProps } from "./base_badge_field";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { Component } from "@odoo/owl";
import { standardFieldProps } from "../standard_field_props";

export class BadgesSelectionField extends Component {
    static template = "web.BadgesSelectionField";
    static props = {
        ...standardFieldProps,
        iconMapping: { type: Object, optional: true },
        allowedSelectionField: { type: String, optional: true },
        badgeLimit: { type: Number, optional: true },
        placeholder: { type: String, optional: true },
        defaultIcon: { type: String, optional: true },
        canDeselect: { type: Boolean, optional: true },
    };
    static defaultProps = {
        iconMapping: {},
    };
    static components = {
        BaseBadgeField,
    };

    get options() {
        const { record, name, allowedSelectionField } = this.props;
        let options = record.fields[name].selection;

        if (allowedSelectionField) {
            const allowedOptions = record.data[allowedSelectionField];
            options = options.filter(([value]) => allowedOptions.includes(value));
        }

        // Map icons to options
        return options.map(([value, label]) => {
            const icon = this.props.iconMapping[value] ?? this.props.defaultIcon;
            return [value, label, icon];
        });
    }

    get string() {
        const recordData = this.props.record.data[this.props.name];
        if (recordData === false) {
            return "";
        }

        const selected = this.options.find((o) => o[0] === recordData);
        if (selected) {
            return selected[1];
        }

        return "";
    }

    get value() {
        return this.props.record.data[this.props.name];
    }

    onChange(value) {
        this.props.record.update({ [this.props.name]: value });
    }

    get baseBadgeProps() {
        return {
            ...extractStandardFieldProps(this.props),
            onChange: this.onChange.bind(this),
            badgeLimit: this.props.badgeLimit,
            placeholder: this.props.placeholder,
            canDeselect: this.props.canDeselect,
            options: this.options,
            string: this.string,
            value: this.value,
        };
    }
}

export const badgesSelectionField = {
    component: BadgesSelectionField,
    displayName: _t("Badges"),
    supportedTypes: ["selection"],
    supportedOptions: [
        {
            label: _t("Maximum Visible Badges"),
            name: "badgeLimit",
            type: "number",
            default: 0,
            placeholder: _t("Unlimited"),
            help: _t("Displays a dropdown if the badge count is higher than this value."),
        },
    ],
    extractProps: ({ options, placeholder, string }, dynamicInfo) => ({
        placeholder: placeholder || string,
        defaultIcon: options.default_icon,
        badgeLimit: options.badgeLimit,
        canDeselect: !dynamicInfo.required,
        iconMapping: options.icon_mapping,
        allowedSelectionField: options.allowed_selection_field,
    }),
};

registry.category("fields").add("badges_selection", badgesSelectionField);
