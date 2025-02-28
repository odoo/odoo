import { useAssignUserCommand } from "@mail/views/web/fields/assign_user_command_hook";

import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { computeM2OProps, Many2One } from "@web/views/fields/many2one/many2one";
import {
    buildM2OFieldDescription,
    extractM2OFieldProps,
    Many2OneField,
} from "@web/views/fields/many2one/many2one_field";
import { Avatar } from "../avatar/avatar";

export class Many2OneAvatarUserField extends Component {
    static template = "mail.Many2OneAvatarUserField";
    static components = { Avatar, Many2One };
    static props = {
        ...Many2OneField.props,
        withCommand: { type: Boolean },
    };

    setup() {
        if (this.props.withCommand) {
            useAssignUserCommand();
        }
    }

    get m2oProps() {
        return computeM2OProps(this.props);
    }

    get relation() {
        // This getter is used by `useAssignUserCommand`
        return this.props.record.fields[this.props.name].relation;
    }

    get value() {
        return this.props.record.data[this.props.name];
    }
}

registry.category("fields").add("many2one_avatar_user", {
    ...buildM2OFieldDescription(Many2OneAvatarUserField),
    additionalClasses: ["o_field_many2one_avatar"],
    extractProps(staticInfo, dynamicInfo) {
        const props = extractM2OFieldProps(staticInfo, dynamicInfo);
        props.withCommand = ["form", "list"].includes(staticInfo.viewType);
        return props;
    },
    listViewWidth: [110],
});
