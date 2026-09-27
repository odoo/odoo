import {
    many2OneAvatarUserField,
    Many2OneAvatarUserField,
    many2OneAvatarUserFieldProps,
} from "@mail/views/web/fields/many2one_avatar_user_field/many2one_avatar_user_field";
import { t, useProps } from "@odoo/owl";
import { registry } from "@web/core/registry";

export class Many2OneAvatarLeaderUserField extends Many2OneAvatarUserField {
    props = useProps({
        ...many2OneAvatarUserFieldProps,
        teamField: t.string(),
    });

    get m2oProps() {
        return {
            ...super.m2oProps,
            context: {
                ...super.m2oProps.context,
                crm_formatted_display_name_team: Number(this.props.record.data[this.props.teamField].id),
            },
        };
    }
}

registry.category("fields").add("many2one_avatar_leader_user", {
    ...many2OneAvatarUserField,
    component: Many2OneAvatarLeaderUserField,
    extractProps: (fieldInfo, dynamicInfo) => ({
        ...many2OneAvatarUserField.extractProps(fieldInfo, dynamicInfo),
        teamField: fieldInfo.attrs.teamField,
    }),
});
