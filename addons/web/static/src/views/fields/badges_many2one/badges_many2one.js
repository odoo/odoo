import { getFieldDomain } from "@web/model/relational_model/utils";
import { useSpecialData } from "@web/views/fields/relational_utils";
import { ConnectionLostError } from "@web/core/network/rpc";
import { BaseBadgeField, extractStandardFieldProps } from "../badges_selection/base_badge_field";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { standardFieldProps } from "../standard_field_props";

export function getMany2oneData() {
    const { record, name, domain: propDomain, relatedIconField, defaultIcon } = this.props;
    const field = record.fields[name];

    return useSpecialData(async (orm) => {
        const domain = getFieldDomain(record, name, propDomain);
        const { relation } = field;

        try {
            if (relatedIconField) {
                const records = await orm.call(relation, "search_read", [], {
                    domain,
                    fields: ["display_name", relatedIconField],
                });

                return records.map((r) => [
                    r.id,
                    r.display_name,
                    r[relatedIconField] || defaultIcon,
                ]);
            }

            return await orm.call(relation, "name_search", ["", domain]);
        } catch (error) {
            if (error instanceof ConnectionLostError) {
                const currentVal = record.data[name];

                if (!currentVal) {
                    return [];
                }

                return [[currentVal.id, currentVal.display_name, defaultIcon]];
            }
            throw error;
        }
    });
}

export class BadgesMany2oneField extends Component {
    static template = "web.BadgesMany2oneField";
    static props = {
        ...standardFieldProps,
        domain: { type: [Array, Function], optional: true },
        relatedIconField: { type: String, optional: true },
        badgeLimit: { type: Number, optional: true },
        placeholder: { type: String, optional: true },
        defaultIcon: { type: String, optional: true },
        canDeselect: { type: Boolean, optional: true },
    };
    static components = {
        BaseBadgeField,
    };

    setup() {
        this.specialData = getMany2oneData.apply(this);
    }

    get options() {
        return this.specialData.data || [];
    }

    get string() {
        const recordData = this.props.record.data[this.props.name];
        return recordData ? recordData.display_name : "";
    }

    get value() {
        const rawValue = this.props.record.data[this.props.name];
        return rawValue ? rawValue.id : rawValue;
    }

    onChange(value) {
        if (!value) {
            this.props.record.update({ [this.props.name]: false });
        } else {
            const option = this.options.find((option) => option[0] === value);
            const relatedIconProp = this.props.relatedIconField
                ? { [this.props.relatedIconField]: option[2] }
                : {};
            this.props.record.update({
                [this.props.name]: { id: option[0], display_name: option[1], ...relatedIconProp },
            });
        }
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

export const badgesMany2oneField = {
    component: BadgesMany2oneField,
    displayName: _t("Badges"),
    supportedTypes: ["many2one"],
    supportedOptions: [
        {
            label: _t("Maximum Visible Badges"),
            name: "badgeLimit",
            type: "number",
            default: 0,
            placeholder: _t("Unlimited"),
            help: _t("Displays a dropdown if the badge count is higher than this value."),
        },
        {
            label: _t("Related Icon Field"),
            name: "related_icon_field",
            type: "string",
            help: _t("Name of the co-model's field that contains the icon class."),
        },
        {
            label: _t("Default Icon"),
            name: "default_icon",
            type: "string",
            help: _t("Fallback icon if co-model's field doesn't contains an icon"),
        },
    ],
    extractProps: ({ options, placeholder, default_icon, string }, dynamicInfo) => ({
        placeholder: placeholder || string,
        defaultIcon: options.default_icon ?? default_icon,
        domain: dynamicInfo.domain,
        canDeselect: !dynamicInfo.required,
        badgeLimit: options.badgeLimit,
        relatedIconField: options.related_icon_field,
    }),
};

registry.category("fields").add("badges_many2one", badgesMany2oneField);
