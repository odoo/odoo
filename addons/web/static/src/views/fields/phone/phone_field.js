/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { useInputField } from "../input_field_hook";
import { standardFieldProps } from "../standard_field_props";

const { Component } = owl;

export class PhoneField extends Component {
    setup() {
        useInputField({ getValue: () => this.props.value || "" });
    }
}

PhoneField.template = "web.PhoneField";
PhoneField.props = {
    ...standardFieldProps,
    placeholder: { type: String, optional: true },
};

PhoneField.displayName = _lt("Phone");
PhoneField.supportedTypes = ["char"];

PhoneField.extractProps = ({ attrs }) => {
    return {
        placeholder: attrs.placeholder,
    };
};

class FormPhoneField extends PhoneField {}
FormPhoneField.template = "web.FormPhoneField";

registry.category("fields").add("phone", PhoneField);
registry.category("fields").add("form.phone", FormPhoneField);
