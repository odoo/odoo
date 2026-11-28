import { Avatar } from "@mail/views/web/fields/avatar/avatar";

import { onWillStart, t, useProps } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { buildM2OFieldDescription } from "@web/views/fields/many2one/many2one_field";
import {
    extractM2OExtendedFieldProps,
    Many2OneExtendedField,
    many2OneExtendedFieldProps,
} from "@hr/views/fields/many2one_extended_field/many2one_extended_field";

export class Many2OneAvatarEmployeeField extends Many2OneExtendedField {
    static template = "hr.Many2OneAvatarEmployeeField";
    static components = { ...Many2OneExtendedField.components, Avatar };
    props = useProps({
        ...many2OneExtendedFieldProps,
        relation: t.string().optional(),
    });

    setup() {
        super.setup();
        onWillStart(async () => {
            this.isHrUser = await user.hasGroup("hr.group_hr_user");
        });
    }

    get m2oProps() {
        return {
            ...super.m2oProps,
            canQuickCreate: false,
            relation: this.relation,
        };
    }

    get relation() {
        return this.props.relation ?? (this.isHrUser ? "hr.employee" : "hr.employee.public");
    }

    get uniqueId() {
        return this.value?.write_date ? this.value.write_date.toMillis() : undefined;
    }
}

registry.category("fields").add("many2one_avatar_employee", {
    ...buildM2OFieldDescription(Many2OneAvatarEmployeeField),
    relatedFields: [{ name: "write_date", type: "datetime" }],
    additionalClasses: ["o_field_many2one_avatar", "o_field_many2one_avatar_user"],
    extractProps(staticInfo, dynamicInfo) {
        return {
            ...extractM2OExtendedFieldProps(staticInfo, dynamicInfo),
            relation: staticInfo.options.relation,
            canOpen:
                "no_open" in staticInfo.options
                    ? !staticInfo.options.no_open
                    : staticInfo.viewType === "form",
        };
    },
});
