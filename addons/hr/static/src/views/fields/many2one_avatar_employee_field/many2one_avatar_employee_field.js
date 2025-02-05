import { AvatarCardEmployeePopover } from "@hr/components/avatar_card_employee/avatar_card_employee_popover";
import { Avatar } from "@mail/views/web/fields/avatar/avatar";
import { Component, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { Many2One, useMany2One } from "@web/views/fields/many2one/many2one";
import {
    buildM2OFieldDescription,
    extractM2OFieldProps,
    Many2OneField,
} from "@web/views/fields/many2one/many2one_field";

class AvatarEmployee extends Avatar {
    static components = { ...super.components, Popover: AvatarCardEmployeePopover };
}

export class Many2OneAvatarEmployeeField extends Component {
    static template = "hr.Many2OneAvatarEmployeeField";
    static components = { Many2One, AvatarEmployee };
    static props = {
        ...Many2OneField.props,
        relation: { type: String, optional: true },
    };

    setup() {
        this.m2o = useMany2One(() => this.props);

        onWillStart(async () => {
            this.isHrUser = await user.hasGroup("hr.group_hr_user");
        });
    }

    get relation() {
        return this.props.relation ?? (this.isHrUser ? "hr.employee" : "hr.employee.public");
    }

    get m2oProps() {
        return {
            ...this.m2o.computeProps(),
            relation: this.relation,
            canQuickCreate: false,
        };
    }
}

registry.category("fields").add("many2one_avatar_employee", {
    ...buildM2OFieldDescription(Many2OneAvatarEmployeeField),
    extractProps(staticInfo, dynamicInfo) {
        return {
            ...extractM2OFieldProps(staticInfo, dynamicInfo),
            relation: staticInfo.options.relation,
        };
    },
});
