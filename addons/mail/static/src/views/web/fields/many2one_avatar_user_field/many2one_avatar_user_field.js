import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { Many2One, useMany2One } from "@web/views/fields/many2one/many2one";
import {
    buildM2OFieldDescription,
    extractM2OFieldProps,
    Many2OneField,
} from "@web/views/fields/many2one/many2one_field";
import { useAssignUserCommand } from "../assign_user_command_hook";
import { Avatar } from "../avatar/avatar";

export class Many2OneAvatarUserField extends Component {
    static template = "mail.Many2OneAvatarUserField";
    static components = { Avatar, Many2One };
    static props = {
        ...Many2OneField.props,
        withCommand: { type: Boolean },
    };

    setup() {
        this.m2o = useMany2One(() => this.props);
        if (this.props.withCommand) {
            useAssignUserCommand();
        }
    }

    get relation() {
        // This getter is used by `useAssignUserCommand`
        // @todo: remove this getter
        return this.m2o.relation;
    }

    get m2oProps() {
        return this.m2o.computeProps();
    }
}

registry.category("fields").add("many2one_avatar_user", {
    ...buildM2OFieldDescription(Many2OneAvatarUserField),
    extractProps(staticInfo, dynamicInfo) {
        const props = extractM2OFieldProps(staticInfo, dynamicInfo);
        props.withCommand = ["form", "list"].includes(staticInfo.viewType);
        return props;
    },
    listViewWidth: [110],
});
