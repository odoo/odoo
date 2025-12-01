import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { getFieldDomain } from "@web/model/relational_model/utils";
import { useSpecialData } from "@web/views/fields/relational_utils";
import {
    badgeSelectionField,
    BadgeSelectionField,
} from "@web/views/fields/badge_selection/badge_selection_field";

/**
 * Extends the standard BadgeSelectionField to support icons and filtering.
 * 1. Many2one: Icons fetched from a related field on the co-model (defined by `relatedIconField`).
 * 2. Selection: Icons mapped via static options (`iconMapping`).
 *    In addition, selection options can be filtered by providing an `allowedSelectionField` field,
 *    a mapping of values to icons (that will be overridden by `iconMapping` if provided).
 */
export class BadgeSelectionWithIconsField extends BadgeSelectionField {
    static props = {
        ...BadgeSelectionField.props,
        defaultIcon: { type: String, optional: true },
        // --- Many2one ---
        relatedIconField: { type: String, optional: true },
        // --- Selection ---
        // Static mapping from XML options: { 'selection_key': 'fa-icon' }
        iconMapping: { type: Object, optional: true },
        // Field name used to filter the visible selection options
        allowedSelectionField: { type: String, optional: true },
    };
    static defaultProps = {
        defaultIcon: "fa-check",
        iconMapping: {},
    };
    static template = "mail.BadgeSelectionIconsField";

    async setup() {
        super.setup();
        this.type = this.props.record.fields[this.props.name].type;

        if (this.type === "many2one") {
            this.specialData = useSpecialData(async (orm, props) => {
                const domain = getFieldDomain(props.record, props.name, props.domain);
                const { relation } = props.record.fields[props.name];

                const ret = await orm.call(relation, "search_read", [], {
                    domain: domain,
                    fields: ["id", "name", props.relatedIconField],
                });

                return ret.map((opt) => {
                    const iconValue = opt[props.relatedIconField] || props.defaultIcon;
                    return [opt.id, opt.name, iconValue];
                });
            });
        }
    }

    get options() {
        if (this.type === "many2one") {
            return this.specialData.data;
        }

        let baseOptions = super.options;
        let icons = {};

        if (this.props.allowedSelectionField) {
            icons = this.props.record.data[this.props.allowedSelectionField];
            const allowedValues = Object.keys(icons);
            baseOptions = baseOptions.filter(([value]) => allowedValues.includes(value));
        }
        Object.assign(icons, this.props.iconMapping);

        return baseOptions.map(([value, label]) => {
            const icon = icons[value] || this.props.defaultIcon;
            return [value, label, icon];
        });
    }
}

export const badgeSelectionWithIconsField = {
    ...badgeSelectionField,
    component: BadgeSelectionWithIconsField,
    supportedTypes: ["many2one", "selection"],
    displayName: _t("Badges with Icons"),
    extractProps: (fieldInfo, dynamicInfo) => {
        const baseProps = badgeSelectionField.extractProps(fieldInfo, dynamicInfo);
        const { options } = fieldInfo;
        return {
            ...baseProps,
            defaultIcon: options.default_icon,
            relatedIconField: options.related_icon_field,
            iconMapping: options.icon_mapping,
            allowedSelectionField: options.allowed_selection_field,
        };
    },
};

registry.category("fields").add("selection_badge_icons", badgeSelectionWithIconsField);
