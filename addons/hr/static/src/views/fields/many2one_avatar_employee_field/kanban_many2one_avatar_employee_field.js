import { AvatarCardEmployeePopover } from "@hr/components/avatar_card_employee/avatar_card_employee_popover";
import { Avatar } from "@mail/views/web/fields/avatar/avatar";
import { Component, onWillStart } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { computeM2OProps, Many2One } from "@web/views/fields/many2one/many2one";
import {
    buildM2OFieldDescription,
    extractM2OFieldProps,
    m2oSupportedOptions,
    Many2OneField,
} from "@web/views/fields/many2one/many2one_field";

class AvatarEmployee extends Avatar {
    static components = { ...super.components, Popover: AvatarCardEmployeePopover };
}

export class KanbanMany2OneAvatarEmployeeField extends Component {
    static template = "hr.Many2OneAvatarEmployeeField";
    static components = { Many2One, AvatarEmployee };
    static props = {
        ...Many2OneField.props,
        displayAvatarName: { type: Boolean, optional: true },
        relation: { type: String, optional: true },
    };

    setup() {
        onWillStart(async () => {
            this.isHrUser = await user.hasGroup("hr.group_hr_user");
        });
    }

    get displayName() {
        return this.props.displayAvatarName && this.value ? this.value[1] : "";
    }

    get m2oProps() {
        return {
            ...computeM2OProps(this.props),
            relation: this.relation,
            canQuickCreate: false,
        };
    }

    get relation() {
        return this.props.relation ?? (this.isHrUser ? "hr.employee" : "hr.employee.public");
    }

    get resId() {
        return this.value && this.value[0];
    }

    get value() {
        return this.props.record.data[this.props.name];
    }
}

/** @type {import("registries").FieldsRegistryItemShape} */
const fieldDescr = {
    ...buildM2OFieldDescription(KanbanMany2OneAvatarEmployeeField),
    extractProps(staticInfo, dynamicInfo) {
        return {
            ...extractM2OFieldProps(staticInfo, dynamicInfo),
            displayAvatarName: staticInfo.options.display_avatar_name || false,
            relation: staticInfo.options.relation,
        };
    },
    supportedOptions: [
        ...m2oSupportedOptions,
        {
            label: _t("Display avatar name"),
            name: "display_avatar_name",
            type: "boolean",
        },
    ],
};

registry.category("fields").add("activity.many2one_avatar_employee", fieldDescr);
registry.category("fields").add("kanban.many2one_avatar_employee", fieldDescr);
