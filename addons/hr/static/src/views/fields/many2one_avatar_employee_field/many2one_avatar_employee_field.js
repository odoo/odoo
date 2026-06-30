import { AvatarEmployee } from "@hr/components/avatar_employee/avatar_employee";
import { Component, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { computeM2OProps, Many2One } from "@web/views/fields/many2one/many2one";
import {
    buildM2OFieldDescription,
    extractM2OFieldProps,
    Many2OneField,
} from "@web/views/fields/many2one/many2one_field";

export class Many2OneAvatarEmployeeField extends Component {
    static template = "hr.Many2OneAvatarEmployeeField";
    static components = { AvatarEmployee, Many2One };
    static props = {
        ...Many2OneField.props,
        relation: { type: String, optional: true },
    };

    setup() {
        onWillStart(async () => {
            this.isHrUser = await user.hasGroup("hr.group_hr_user");
        });
    }

    get m2oProps() {
        return {
            ...computeM2OProps(this.props),
            canQuickCreate: false,
            relation: this.relation,
        };
    }

    get relation() {
        return this.props.relation ?? (this.isHrUser ? "hr.employee" : "hr.employee.public");
    }
}

registry.category("fields").add("many2one_avatar_employee", {
    ...buildM2OFieldDescription(Many2OneAvatarEmployeeField),
    additionalClasses: [
        "o_field_many2one_avatar",
        "o_field_many2one_avatar_kanban",
        "o_field_many2one_avatar_user",
    ],
    extractProps(staticInfo, dynamicInfo) {
        return {
            ...extractM2OFieldProps(staticInfo, dynamicInfo),
            relation: staticInfo.options.relation,
            canOpen: "no_open" in staticInfo.options
                ? !staticInfo.options.no_open
                : staticInfo.viewType === "form",
        };
    },
});
