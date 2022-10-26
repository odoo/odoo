/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { useInputField } from "../input_field_hook";
import { standardFieldProps } from "../standard_field_props";

const { Component } = owl;

export class EmailField extends Component {
    setup() {
        useInputField({ getValue: () => this.props.value || "" });
    }
}

EmailField.template = "web.EmailField";
EmailField.props = {
    ...standardFieldProps,
    placeholder: { type: String, optional: true },
};
EmailField.extractProps = ({ attrs }) => {
    return {
        placeholder: attrs.placeholder,
    };
};

EmailField.displayName = _lt("Email");
EmailField.supportedTypes = ["char"];

class FormEmailField extends EmailField {}
FormEmailField.template = "web.FormEmailField";

registry.category("fields").add("email", EmailField);
registry.category("fields").add("form.email", FormEmailField);
