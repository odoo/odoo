// @ts-check
/** @odoo-module native */
import { registry } from "@web/core/registry";
import { _t } from "@web/core/translation";
import { useSpecialData } from "@web/fields/relational/special_data";
import {
    BadgeSelectionField,
    badgeSelectionField,
} from "@web/fields/selection/badge_selection/badge_selection_field";
import { getFieldDomain } from "@web/model/relational_model";
/**
 * @typedef {Object} Props
 * @property {String} iconField
 * @property {String} defaultIcon
 */
export class BadgeSelectionWithIconsField extends BadgeSelectionField {
    static props = {
        ...BadgeSelectionField.props,
        iconField: { type: String },
        defaultIcon: { type: String, optional: true },
    };
    static template = "mail.BadgeSelectionIconsField";
    static defaultProps = {
        ...BadgeSelectionField.defaultProps,
        defaultIcon: "fa-check",
    };

    setup() {
        this.type = this.props.record.fields[this.props.name].type;
        this.specialData = useSpecialData(
            /**
             * @param {import("@web/core/network/orm_service").ORM} orm
             * @param {Object} props
             */
            async (orm, props) => {
                const domain = getFieldDomain(props.record, props.name, props.domain);
                const { relation } = props.record.fields[props.name];
                const ret = await orm.call(relation, "search_read", [], {
                    domain: domain,
                    fields: ["id", "name", props.iconField],
                });
                return ret.map((option) => [
                    option.id,
                    option.name,
                    option[props.iconField] || props.defaultIcon,
                ]);
            },
        );
    }
}

export const badgeSelectionWithIconsField = {
    ...badgeSelectionField,
    component: BadgeSelectionWithIconsField,
    supportedTypes: ["many2one"],
    displayName: _t("Badges with Icons"),
    /**
     * @param {{attrs: Object}} fieldInfo
     * @param {Object} dynamicInfo
     * @returns {Object}
     */
    extractProps: (fieldInfo, dynamicInfo) => ({
        ...badgeSelectionField.extractProps(fieldInfo, dynamicInfo),
        iconField: fieldInfo.attrs.iconField,
        defaultIcon: fieldInfo.attrs.defaultIcon,
    }),
};
registry.category("fields").add("selection_badge_icons", badgeSelectionWithIconsField);
