/** @odoo-module **/

import { _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useInputField } from "@web/views/fields/input_field_hook";

import { recommendations, ConcretePolicy } from "./password_policy";
import { Meter } from "./password_meter";

const { Component, xml, onWillStart, useState } = owl;

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
PasswordField.template = xml`
<span t-if="props.readonly" t-out="props.value and '*'.repeat(props.value.length)"/>
<t t-else="">
    <input class="o_input o_field_password" type="password"
           t-att-id="props.id" t-ref="input" placeholder=" "
           t-on-input="ev => this.state.value = ev.target.value"/>
    <Meter password="state.value"
           required="state.required"
           recommended="recommendations"/>
</t>
`;

registry.category("fields").add("password_meter", PasswordField);
