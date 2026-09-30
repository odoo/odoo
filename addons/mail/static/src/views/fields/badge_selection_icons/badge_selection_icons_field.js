import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { getFieldDomain } from "@web/model/relational_model/utils";
import { useSpecialData } from "@web/views/fields/relational_utils";
import {
    badgeSelectionField,
    BadgeSelectionField,
} from "@web/views/fields/badge_selection/badge_selection_field";

/**
 * @typedef BadgeSelectionIconsField
 * Overrides the standard BadgeSelectionField and inserts FontAwesome icons before each option's title.
 * Only compatible with Many2one selectors. Related options should have an "icon" field, the name
 * of which should be specified through the iconField prop.
 *
 * Special props:
 * @param {String} iconField The name of the field on which the icon is stored on the many2one option
 * @param {String} defaultIcon If the field pointed through iconField is empty on the related record, a default fa icon can be specified.
 */
export class BadgeSelectionWithIconsField extends BadgeSelectionField {
    static props = {
        ...BadgeSelectionField.props,
        iconField: { type: String },
        defaultIcon: { type: String, optional: true, default: "fa-check" },
    };
    static template = "mail.BadgeSelectionIconsField";

    /**
     * @override
     * many2one fields use attribute "specialData" to store information pertaining to many2one relations.
     * As such, this.specialData is used by the inherited BadgeSelectionField to store the Many2one selection options for this field.
     */
    async setup() {
        this.type = this.props.record.fields[this.props.name].type;
        this.specialData = useSpecialData(async (orm, props) => {
            const domain = getFieldDomain(props.record, props.name, props.domain);
            const { relation } = props.record.fields[props.name];
            const ret = await orm.call(relation, "search_read", [], {
                domain: domain,
                fields: ["id", "name", props.iconField],
            });
            return ret.map((opt) => {
                const option = Object.values(opt);
                if (!option[2]) {
                    option[2] = props.defaultIcon;
                }
                return option;
            });
        });
    }
}

export const badgeSelectionWithIconsField = {
    ...badgeSelectionField,
    component: BadgeSelectionWithIconsField,
    supportedTypes: ["many2one"],
    displayName: _t("Badges with Icons"),
    extractProps: (fieldInfo, dynamicInfo) => ({
        ...badgeSelectionField.extractProps(fieldInfo, dynamicInfo),
        iconField: fieldInfo.attrs.iconField,
        defaultIcon: fieldInfo.attrs.defaultIcon,
    }),
};
registry.category("fields").add("selection_badge_icons", badgeSelectionWithIconsField);
