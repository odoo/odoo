import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { getFieldDomain } from "@web/model/relational_model/utils";
import { useSpecialData } from "@web/views/fields/relational_utils";
import { badgeSelectionField, BadgeSelectionField } from "@web/views/fields/badge_selection/badge_selection_field";


export class BadgeSelectionWithIconsField extends BadgeSelectionField {
    static props = {
        ...BadgeSelectionField.props,
        iconField: { type: String, },
        defaultIcon: { type: String, optional: true, default: "fa-check"}
    };
    static template="mail.BadgeSelectionIconsField";

    async setup() {
        this.type = this.props.record.fields[this.props.name].type;
        if (this.type === "many2one") {
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
                        option[2] = "fa-check";
                    }
                    return option;
                })
            });
        }
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
    // todo: check if displayName is for display in Studio, and if it is disable it or make sure it can be used
}
registry.category("fields").add("selection_badge_icons", badgeSelectionWithIconsField);
