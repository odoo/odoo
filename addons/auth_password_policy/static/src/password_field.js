/** @odoo-module **/

import { _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useInputField } from "@web/views/fields/input_field_hook";

import { recommendations, ConcretePolicy } from "./password_policy";
import { Meter } from "./password_meter";

const { Component, onWillStart, useState } = owl;

export class PasswordField extends Component {
    setup() {
        this.state = useState({
            required: new ConcretePolicy({}),
            value: "",
        });

        useInputField({
            getValue: () => this.props.value || "",
        });

        const orm = useService("orm");
        onWillStart(async () => {
            const policy = await orm.call("res.users", "get_password_policy");
            this.state.required = new ConcretePolicy(policy);
        });
        this.recommendations = recommendations;
    }
}
PasswordField.displayName = _lt("Password");
PasswordField.supportedTypes = ["char"];
PasswordField.props = standardFieldProps;
PasswordField.components = { Meter };
PasswordField.template = "auth_password_policy.PasswordField";
registry.category("fields").add("password_meter", PasswordField);
